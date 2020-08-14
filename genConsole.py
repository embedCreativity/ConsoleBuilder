#!/usr/bin/env python3

'''
  Copyright (C) 2020 Embed Creativity LLC

  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License along
  with this program; if not, write to the Free Software Foundation, Inc.,
  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
'''

import sys
import xml.etree.ElementTree as ET
from enum import Enum
from datetime import datetime

class Node:
    def __init__(self, name='~'):
        self.name = name
        self.parent = None
        self.children = []
        self.description = ''
        self.isMethod = False
        self.methodName = ''
        self.hasParams = False
        self.strVarParamDesc = ''
        self.strVarNodeName = ''
        self.strVarBranchArrayName = None
        self.arrStrVarNodeNames = []

    def addChild(self, child):
        self.children.append(child)

    def setParent(self, parent):
        self.parent = parent

    def setDescription(self, description):
        self.description = description


class StringType(Enum):
    STR_COMMAND = 1
    STR_DESCRIPTION = 2

#############################################################
# Code Generation Templates                                 #

# Template file
TEMPLATE_FILE               = 'CommandTreeTemplate.c'
OUTPUT_FILE                 = 'foo.c'

# Template strings correlate to the code template source,
#   where we're going to replace these keywords with our
#   generated source
TEMPLATE_METHOD_FORWARDS    = 'METHOD_FUNC_FORWARD_DECLARATIONS'
TEMPLATE_STRINGS            = 'STRING_DECLARATIONS'
TEMPLATE_BRANCHES           = 'BRANCH_DECLARATIONS'
TEMPLATE_NODES              = 'NODE_DECLARATIONS'

METHOD_FORWARD              = 'bool FUNCTION (const char *userInput);'
METHOD_PROTO = ''                                       +\
    '// DESCRIPTION:\n'                                 +\
    '//   DESC_PLACEHOLDER\n'                           +\
    '// PARAMS:\n'                                      +\
    'PARAM_PLACEHOLDER\n'                               +\
    'bool FUNCTION (const char *userInput)\n'           +\
    '{\n'                                               +\
    'INPUT_VERIFICATION_METHOD\n'                       +\
    '\n'                                                +\
    '    printf("You have called: FUNCTION\\n");\n'     +\
    '    return true;\n'                                +\
    '}\n'

VOID_CHECK = ''                                         +\
    '    if ( NULL != userInput )\n'                    +\
    '    {\n'                                           +\
    '        return false;\n'                           +\
    '    }'

# 'Address of' prefix we insert before variable names
REF = '&'

STR_COMMAND_PREFIX      = 'strCmd'
STR_DESCRIPTION_PREFIX  = 'strDesc'
STR_DECLARATION_PROTO   = 'static const char NAME[] = "STRING";'

# VARNAME_NODE prefix
STR_NODE_PREFIX             = 'node'
# VARNAME_CHILDREN prefix
STR_NODE_CHILDREN_PREFIX    = 'arrNode'

# We create an array of pointers to other nodes - the branches a node has
# Note the '*' that prefixes the variable name, indicating we're creating an array of pointers
# CHILDREN is an array of pointers to nodes (e.g., {&node1, &node2, &node3} )
NODE_CHILDREN_PROTO     = ''                                                    +\
    'static const commandTreeNode_t* VARNAME_CHILDREN[] = {CHILDREN};'

# Declaration of a node - the children created above gets assigned in VARNAME_CHILDREN
NODE_PROTO              = ''                                                    +\
    'static const commandTreeNode_t  VARNAME_NODE = { .name=STR_KEY, .desc=DESC, '  +\
    '.method=METHOD, .argDesc=ARG_HELP, .childCount=COUNT_CHILDREN, .children=VARNAME_CHILDREN };'

#############################################################

class genConsole:

    def __init__(self, path):
        self.path = path
        self.codeMethodImplementations = []
        self.codeMethodForwardDeclarations = []
        self.codeCmdStringDeclarations = []
        self.codeDescStringDeclarations = []
        self.codeNodeDeclarations = []
        self.cmdStringMap = {}
        self.descriptionStringMap = {}
        self.flattenedTree = []
        self.nodeRoot = Node() # N-ary tree

    def debugPrintNode(self, node):
        print('NAME: {}'.format(node.name))
        if node.parent is None:
            print('  PARENT: None')
        else:
            print('  PARENT: {}'.format(node.parent.name))

        print('  DESCRIPTION: {}'.format(node.description))
        print('  IS_METHOD: {}'.format(node.isMethod))
        print('  METHOD_NAME: {}'.format(node.methodName))
        print('  STRVARNODENAME: {}'.format(node.strVarNodeName))
        if ( node.strVarBranchArrayName is not None ):
            print('  STRVARBRANCHARRAYNAME: {}'.format(node.strVarBranchArrayName))
        else:
            print('  STRVARBRANCHARRAYNAME: NONE')
        print('  ARRSTRVARNODENAMES[]: {}'.format(node.arrStrVarNodeNames))
        print('  {} CHILDREN - CALLING NOW'.format(len(node.children)))
        for child in node.children:
            self.debugPrintNode(child)

    def createBranchNode(self, parent, varCmd, varDesc):
        # python N-ary tree maintenance
        node = Node(varCmd)
        node.setParent(parent)
        node.setDescription(varDesc)
        # create variable name for the commandTreeNode_t declaration
        node.strVarNodeName = STR_NODE_PREFIX + str(len(self.flattenedTree) + 1)
        parent.addChild(node)
        # Create a variable name for the array object if it does not exist
        if ( parent.strVarBranchArrayName is None ):
            parent.strVarBranchArrayName = STR_NODE_CHILDREN_PREFIX + str(len(self.flattenedTree) + 1)
        # Add this new node to the parent's array object
        parent.arrStrVarNodeNames.append(node.strVarNodeName)
        # Add the new node to the flattened Node Tree array
        self.flattenedTree.append(node)

        return node

    def convertMethodNode(self, node, methodName, hasParams=False, paramsDesc=''):
        node.isMethod = True
        node.methodName = methodName
        node.hasParams = hasParams
        if hasParams:
            node.strVarParamDesc = self.getStringVarName(StringType.STR_DESCRIPTION, paramsDesc)
            print('{}: {} returned {}'.format(methodName, paramsDesc, node.strVarParamDesc))

    def createFunctionPrototype(self, method, description, params):
        paramLine = ''
        formatNotes = ''
        formatVerification = '    // TODO:\n'

        if len(params) > 0:
            for param in params:
                paramLine += '{} {},'.format(param['type'], param['name'])
                if 'format' in param:
                    formatNotes += '//    {} {} format: {}\n'.format(param['type'],
                                    param['name'], param['format'])
                    formatVerification += '    //   Validate user input and convert to name: {}, type: {}, format: {}\n'.format(param['name'], param['type'], param['format'])
                else:
                    formatNotes += '//    {} {}\n'.format(param['type'], param['name'])
                    formatVerification += '    //   Validate user input and convert to name: {}, type: {}\n'.format(param['name'], param['type'])
            paramLine = paramLine[:-1] # trim that last comma character
            formatNotes = formatNotes[:-1] # trim last newline
            formatVerification = formatVerification[:-1] # trim last newline
        else:
            formatNotes += '//    VOID'
            formatVerification = VOID_CHECK

        functionDeclaration = METHOD_PROTO
        functionDeclaration = functionDeclaration.replace('DESC_PLACEHOLDER', description)
        functionDeclaration = functionDeclaration.replace('FUNCTION', method)
        functionDeclaration = functionDeclaration.replace('ARGLIST', paramLine)
        functionDeclaration = functionDeclaration.replace('PARAM_PLACEHOLDER', formatNotes)
        functionDeclaration = functionDeclaration.replace('INPUT_VERIFICATION_METHOD', formatVerification)
        forwardDeclaration  = METHOD_FORWARD
        forwardDeclaration  = forwardDeclaration.replace('FUNCTION', method)
        forwardDeclaration  = forwardDeclaration.replace('ARGLIST', paramLine)

        self.codeMethodImplementations.append(functionDeclaration)
        self.codeMethodForwardDeclarations.append(forwardDeclaration)

    def createBranchPrototypes(self):

        for node in self.flattenedTree:
            # common strings
            name = node.name
            description = node.description
            strVarNode = node.strVarNodeName

            # Format the object declaration and insert into list
            nodeDeclaration = NODE_PROTO
            nodeDeclaration = nodeDeclaration.replace('VARNAME_NODE', strVarNode)
            if name is None:
                name = 'NULL'
            nodeDeclaration = nodeDeclaration.replace('STR_KEY', name)

            if description is None:
                description = 'NULL'
            nodeDeclaration = nodeDeclaration.replace('DESC', description)

            if node.isMethod:
                methodName = node.methodName
                strVarParamDesc = node.strVarParamDesc

                nodeDeclaration = nodeDeclaration.replace('METHOD', methodName)
                print('createBranchPrototypes: method: {}, help: {}'.format(methodName, strVarParamDesc))
                if node.hasParams:
                    nodeDeclaration = nodeDeclaration.replace('ARG_HELP', strVarParamDesc)
                else:
                    nodeDeclaration = nodeDeclaration.replace('ARG_HELP', 'NULL')
                nodeDeclaration = nodeDeclaration.replace('COUNT_CHILDREN', '0')
                nodeDeclaration = nodeDeclaration.replace('VARNAME_CHILDREN', 'NULL')
                self.codeNodeDeclarations.append(nodeDeclaration)

            else:
                strVarBranches = node.strVarBranchArrayName
                nodeDeclaration = nodeDeclaration.replace('METHOD', 'NULL')
                nodeDeclaration = nodeDeclaration.replace('ARG_HELP', 'NULL')
                nodeDeclaration = nodeDeclaration.replace('COUNT_CHILDREN', str(len(node.children)))
                nodeDeclaration = nodeDeclaration.replace('VARNAME_CHILDREN', strVarBranches)
                self.codeNodeDeclarations.append(nodeDeclaration)

                arrBranches = node.arrStrVarNodeNames

                strBranches = ''
                for branch in arrBranches:
                    strBranches = strBranches + REF + branch + ', '
                # trim trailing comma
                strBranches = strBranches[:-2]

                # Format the object declaration and insert into list
                branchDeclaration = NODE_CHILDREN_PROTO
                branchDeclaration = branchDeclaration.replace('VARNAME_CHILDREN', strVarBranches)
                branchDeclaration = branchDeclaration.replace('CHILDREN', strBranches)
                self.codeNodeDeclarations.append(branchDeclaration)

    def getStringVarName(self, type, inputStr):
        if type == StringType.STR_COMMAND:
            if inputStr in self.cmdStringMap:
                strVarName = self.cmdStringMap[inputStr]
            else:
                strVarName = STR_COMMAND_PREFIX + str(len(self.cmdStringMap) + 1)
                self.cmdStringMap[inputStr] = strVarName
                strTemp = STR_DECLARATION_PROTO
                strTemp = strTemp.replace('NAME', strVarName)
                strTemp = strTemp.replace('STRING', inputStr.upper())
                self.codeCmdStringDeclarations.append(strTemp)
        elif type == StringType.STR_DESCRIPTION:
            if inputStr in self.descriptionStringMap:
                strVarName = self.descriptionStringMap[inputStr]
            else:
                strVarName = STR_DESCRIPTION_PREFIX + str(len(self.descriptionStringMap) + 1)
                self.descriptionStringMap[inputStr] = strVarName
                strTemp = STR_DECLARATION_PROTO
                strTemp = strTemp.replace('NAME', strVarName)
                strTemp = strTemp.replace('STRING', inputStr)
                self.codeDescStringDeclarations.append(strTemp)
        else:
            raise ValueError('UNKNOWN STRING TYPE FOUND: {} -> {}'.format(type, inputStr))
        return strVarName

    def processCommands(self, commands, parent=None):

        if parent == None:
            parent = self.nodeRoot
            parent = self.createBranchNode(parent, None, None)

        for command in commands:
            # Get (sub)Command text
            cmdName = command.attrib['text']
            # get a variable name for the command string
            strVarCmdName = self.getStringVarName(StringType.STR_COMMAND, cmdName)

            # Get Description
            description = command.find('description').text.strip()
            # get a variable name for the description string
            strVarDescName = self.getStringVarName(StringType.STR_DESCRIPTION, description)

            # Create cmd tree object
            node = self.createBranchNode(parent, strVarCmdName, strVarDescName)

            # Either subcommands can be present, or callMethod (with optional arguments), but not both
            methods = command.findall('callMethod')
            subCommands = command.findall('command')
            # callMethod
            if 1 == len(methods) and 0 == len(subCommands):
                methodName = methods[0].attrib['function']
                paramList = methods[0].findall('param')
                params = []
                hasParams = False
                paramHelp = ''
                for param in paramList:
                    hasParams = True
                    paramType = param.find('type').text
                    paramName = param.find('name').text
                    paramDescription = param.find('description').text
                    # Format the argument description (paramHelp) that will be displayed in help context
                    # Also, create the function prototype notes for parameters (params[{}])
                    paramFormat = param.find('format') # optional
                    if paramFormat is not None:
                        paramFormat = paramFormat.text
                        paramHelp = paramHelp + 'Name: ' + paramName +\
                                            ', Type: ' + paramType + ', Format: ' + paramFormat + '\n'
                        params.append({'type': paramType, 'name': paramName, 'description': paramDescription, 'format': paramFormat})
                    else:
                        paramHelp = paramHelp + 'Name: ' + paramName +\
                                            ', Type: ' + paramType + '\n'
                        params.append({'type': paramType, 'name': paramName, 'description': paramDescription})

                if hasParams:
                    paramHelp = paramHelp[:-1] # remove last newline
                    self.convertMethodNode(node, methodName, hasParams, paramHelp)
                else:
                    self.convertMethodNode(node, methodName)
                self.createFunctionPrototype(methodName, description, params)

            # subcommands
            elif 0 == len(methods) and 0 < len(subCommands):
                self.processCommands(subCommands, node)
            else:
                raise ValueError('ERROR: Command must be followed by either sub-commands or one call to a method (and optional arguments), but not both')

    def start(self):
        tree = ET.parse(self.path)
        self.xmlRoot = tree.getroot()

        # Process commands
        commands = self.xmlRoot.findall('command')
        self.processCommands(commands)

        with open(TEMPLATE_FILE) as f:
            fileData = f.read()

            # Process collected command string declarations
            codeStrings = ''
            for string in self.codeCmdStringDeclarations:
                codeStrings += string + '\n'

            # Process collected description string declarations
            for string in self.codeDescStringDeclarations:
                codeStrings += string + '\n'

            # Process collected function declarations
            codeForwardDeclarations = ''
            for declaration in self.codeMethodForwardDeclarations:
                codeForwardDeclarations += declaration + '\n'

            # Create all of the commandTreeNode_t declarations
            self.createBranchPrototypes()
            codeNodes = ''
            for declaration in reversed(self.codeNodeDeclarations):
                codeNodes += declaration + '\n'

            fileData = fileData.replace(TEMPLATE_METHOD_FORWARDS, codeForwardDeclarations)
            fileData = fileData.replace(TEMPLATE_STRINGS, codeStrings)
            fileData = fileData.replace(TEMPLATE_NODES, codeNodes)

            # Process collected function declarations
            for declaration in self.codeMethodImplementations:
                fileData += declaration + '\n'

        with open(OUTPUT_FILE, 'w') as f:
            now = datetime.now()
            fileData = fileData.replace('CODE_GENERATION_DATE', '{}'.format(now))
            f.write(fileData)

        #self.debugPrintNode(self.nodeRoot)

if (__name__ == '__main__' ):
    if len(sys.argv) != 2:
        print('USAGE: {} <path_to_xml_input_file>'.format(sys.argv[0]))
    else:
        foo = genConsole(sys.argv[1])
        foo.start()

