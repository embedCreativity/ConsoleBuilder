#!/usr/bin/env python3

'''
  Copyright (C) 2021 Embed Creativity LLC

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
import argparse

class Node:
    def __init__(self, name='~'):
        self.name = name
        self.parent = None
        self.children = []
        self.description = ''
        self.isMethod = False
        self.isGateway = False
        self.endPoints = []
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

# helper function for getting boolean from argparse
def str2bool(v):
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected')

#############################################################
# Code Generation Templates                                 #

# Template file
TEMPLATE_FILE               = 'CommandTreeTemplate.c'
TEMPLATE_METHOD_HEADER_FILE = 'MethodTemplate.h'
TEMPLATE_METHOD_SOURCE_FILE = 'MethodTemplate.c'
TEMPLATE_PARSER_SOURCE_FILE = 'ParserTemplate.c'

# Template strings correlate to the code template source,
#   where we're going to replace these keywords with our
#   generated source
TEMPLATE_METHOD_FORWARDS    = 'METHOD_FUNC_FORWARD_DECLARATIONS'
TEMPLATE_STRINGS            = 'STRING_DECLARATIONS'
TEMPLATE_HEADER_EXT         = 'EXTERNAL_HEADER'
TEMPLATE_NODES              = 'NODE_DECLARATIONS'
TEMPLATE_METHOD_STUBS       = 'FUNCTION_STUBS'
TEMPLATE_PARSING_ROUTINES   = 'EXAMPLE_PARSING_ROUTINES'

INCLUDE_HEADER              = '#include "FILENAME"\n'
EXTERN_METHOD_PROTO         = 'extern '
METHOD_FORWARD              = 'bool FUNCTION(const char* userInput);'
METHOD_PROTO = ''                                       +\
    '// DESCRIPTION:\n'                                 +\
    '//   DESC_PLACEHOLDER\n'                           +\
    '// PARAMS:\n'                                      +\
    'PARAM_PLACEHOLDER\n'                               +\
    'bool FUNCTION(const char* userInput)\n'            +\
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

    def __init__(self, inputPath, outputPath, externalize):
        self.inputPath = inputPath
        self.outputPath = outputPath
        self.externalize = externalize
        if self.externalize:
            if -1 == self.outputPath.find('.c'):
                self.methodHeaderPath = self.outputPath + 'Methods.h'
                self.outputPath += '.c'
            else:
                self.methodHeaderPath = self.outputPath[:self.outputPath.find('.')] + 'Methods.h'

        self.codeMethodImplementations = []
        self.codeMethodForwardDeclarations = []
        self.codeCmdStringDeclarations = []
        self.codeDescStringDeclarations = []
        self.codeNodeDeclarations = []
        self.cmdStringMap = {}
        self.descriptionStringMap = {}
        self.flattenedTree = []
        self.rootNodes = []

    def debugPrintNode(self, node):
        print('NAME: {}'.format(node.name))
        if node.parent is None:
            print('  PARENT: None')
        else:
            print('  PARENT: {}'.format(node.parent.name))

        print('  DESCRIPTION: {}'.format(node.description))
        print('  HAS_PARAMS: {}'.format(node.hasParams))
        print('  STRVARPARAMDESC: {}'.format(node.strVarParamDesc))
        print('  IS_METHOD: {}'.format(node.isMethod))
        print('  IS_GATEWAY: {}'.format(node.isGateway))
        if node.isGateway:
            for endpoint in node.endPoints:
                print('    EndPoint: {}'.format(endpoint))
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

    def createBranchNode(self, parent, varCmd, varDesc, name=None):
        # python N-ary tree maintenance
        node = Node(varCmd)
        node.setParent(parent)
        node.setDescription(varDesc)
        # create variable name for the commandTreeNode_t declaration
        if name is not None:
            node.strVarNodeName = STR_NODE_PREFIX + str(name)
        else:
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
    
    def convertGatewayNode(self, node, methodName, paramsDesc='', endpoints=[]):
        node.isMethod = True
        node.isGateway = True
        node.methodName = methodName
        node.hasParams = True
        node.strVarParamDesc = self.getStringVarName(StringType.STR_DESCRIPTION, paramsDesc)
        node.endPoints = endpoints

    def createFunctionPrototype(self, method, description, params, endpointNames=None):
        paramLine = ''
        formatNotes = ''
        formatVerification = '    // TODO:\n'

        if len(params) > 0:
            for param in params:
                paramLine += '{} {},'.format(param['type'], param['name'])
                if 'format' in param:
                    formatNotes +=        '//    {} Type: {}, Format: {}\n'.format(param['name'], param['type'], param['format'])
                    formatVerification += '    //   Validate user input and convert to name: {}, type: {}, format: {}\n'.format(param['name'], param['type'], param['format'])
                else:
                    formatNotes +=        '//    {} Type: {}\n'.format(param['name'], param['type'])
                    formatVerification += '    //   Validate user input and convert to name: {}, type: {}\n'.format(param['name'], param['type'])
                if 'description' in param:
                    formatNotes +=        '//        Description: {}\n'.format(param['description'])
                    formatVerification += '    //        Description: {}\n'.format(param['description'])

            # For Gateway Methods
            if endpointNames is not None:
                description += ' (GATEWAY METHOD)'
                for endpoint in endpointNames:
                    formatVerification += '    //          Target EndPoint: &{}\n'.format(endpoint)
                formatVerification += '    //\n'
                formatVerification += '    //          Create a switch or multiple if/else statements based on userInput\n'
                formatVerification += '    //          that sets rootNode to one of each of the Target EndPoints listed\n'
                formatVerification += '    //          above. Example (using &nodeFooBar):\n'
                formatVerification += '    //            if ( 0 == strncmp(userInput, "FOO", USER_INPUT_BUF_SIZE))\n'
                formatVerification += '    //            {\n'
                formatVerification += '    //                 rootNode = &nodeFooBar;\n'
                formatVerification += '    //            }\n'

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
        if ( self.externalize ):
            forwardDeclaration  = EXTERN_METHOD_PROTO + METHOD_FORWARD
        else:
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
            parent = Node() # new N-ary tree
            self.rootNodes.append(parent)
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

            # subcommands can be present, or callMethod (with optional arguments), but not both

            # Gateway check
            isGateway = 'type' in command.attrib and 'Gateway' == command.attrib['type']
            if isGateway:
                methods = command.findall('dispatch')
                # Subcommands are masked for a gateway
                subCommands = []
            else:
                methods = command.findall('callMethod')
                subCommands = command.findall('command')

            # callMethod
            if 1 == len(methods) and 0 == len(subCommands):
                methodName = methods[0].attrib['function']
                paramList = methods[0].findall('param')
                params = []
                hasParams = False
                paramHelp = ''
                iParam = 0 # used to track which param from paramList we are currently processing
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
                        if len(paramList) > 1 and iParam < (len(paramList) - 1):
                            paramHelp = paramHelp + '[Name: ' + paramName +\
                                                    ', Type: ' + paramType + ', Format: ' + paramFormat +\
                                                    ', Desc: ' + paramDescription + '], '
                        else:
                            paramHelp = paramHelp + '[Name: ' + paramName +\
                                                    ', Type: ' + paramType + ', Format: ' + paramFormat +\
                                                    ', Desc: ' + paramDescription + ']\n'
                        params.append({'type': paramType, 'name': paramName, 'description': paramDescription, 'format': paramFormat})
                    else:
                        if len(paramList) > 1 and iParam < (len(paramList) - 1):
                            paramHelp = paramHelp + '[Name: ' + paramName + ', Type: ' + paramType +\
                                                    ', Desc: ' + paramDescription + '], '
                        else:
                            paramHelp = paramHelp + '[Name: ' + paramName + ', Type: ' + paramType +\
                                                    ', Desc: ' + paramDescription + ']\n'
                        params.append({'type': paramType, 'name': paramName, 'description': paramDescription})
                    iParam += 1 # increment our tracker

                # A Gateway must have parameters
                if isGateway and not hasParams:
                    raise ValueError('ERROR: A Gateway must have parameters')
                elif isGateway:
                    # Process the gateway method
                    paramHelp = paramHelp[:-1] # remove last newline
                    endpoints = methods[0].findall('endpoint')
                    endpointNames = []
                    for endpoint in endpoints:
                        endpointNames.append(str(STR_NODE_PREFIX+endpoint.attrib['name']))

                    self.convertGatewayNode(node, methodName, paramHelp, endpointNames)

                    # Then process all commands under this new endpoint (unlink parent)
                    for endpoint in endpoints:
                        # Create root node for each end point
                        root = Node() # new N-ary tree
                        self.rootNodes.append(root)
                        root = self.createBranchNode(root, None, None, endpoint.attrib['name'])
                        # Tie all commands under the endpoint to it
                        endpointcommands = endpoint.findall('command')
                        self.processCommands(endpointcommands, root)

                # Regular method (optional parameters)
                elif hasParams:
                    paramHelp = paramHelp[:-1] # remove last newline
                    self.convertMethodNode(node, methodName, hasParams, paramHelp)
                else:
                    self.convertMethodNode(node, methodName)
                if isGateway:
                    self.createFunctionPrototype(methodName, description, params, endpointNames)
                else:
                    self.createFunctionPrototype(methodName, description, params)

            # subcommands
            elif 0 == len(methods) and 0 < len(subCommands):
                self.processCommands(subCommands, node)
            else:
                print("DEBUG: cmdName = {}, strVarCmdName = {}, description = {}, strVarDescName = {}".format(cmdName, strVarCmdName, description, strVarDescName))
                print("DEBUG: methods = [{}]".format(methods))
                print("DEBUG: subCommands = [{}]".format(subCommands))
                raise ValueError('ERROR: Command must be followed by either sub-commands or one call to a method (and optional arguments), but not both')


    def start(self):
        tree = ET.parse(self.inputPath)
        self.xmlRoot = tree.getroot()

        # Process commands
        commands = self.xmlRoot.findall('command')
        self.processCommands(commands)

        #for node in self.rootNodes:
        #    self.debugPrintNode(node)
        #quit()

        with open(TEMPLATE_FILE) as fin:
            consoleFileData = fin.read()

            # Process collected command string declarations
            codeStrings = ''
            for string in self.codeCmdStringDeclarations:
                codeStrings += string + '\n'

            # Process collected description string declarations
            for string in self.codeDescStringDeclarations:
                codeStrings += string + '\n'
            # remove final newline
            codeStrings = codeStrings[:-1]

            # Process collected function declarations
            codeForwardDeclarations = ''
            for declaration in self.codeMethodForwardDeclarations:
                codeForwardDeclarations += declaration + '\n'
            # remove final newline
            codeForwardDeclarations = codeForwardDeclarations[:-1]

            # Create all of the commandTreeNode_t declarations
            self.createBranchPrototypes()
            codeNodes = ''
            for declaration in reversed(self.codeNodeDeclarations):
                codeNodes += declaration + '\n'
            # Remove final newline
            codeNodes = codeNodes[:-1]

            consoleFileData = consoleFileData.replace(TEMPLATE_METHOD_FORWARDS, codeForwardDeclarations)
            consoleFileData = consoleFileData.replace(TEMPLATE_STRINGS, codeStrings)
            consoleFileData = consoleFileData.replace(TEMPLATE_NODES, codeNodes)

            # create separate source and header file for methods if self.externalize == true
            if self.externalize:
                includeString = INCLUDE_HEADER.replace('FILENAME', self.methodHeaderPath)
                consoleFileData = consoleFileData.replace(TEMPLATE_HEADER_EXT, includeString)
                # remove parameter parsing placeholder
                consoleFileData = consoleFileData.replace(TEMPLATE_PARSING_ROUTINES, '')

                # Generate Method Source File
                with open(TEMPLATE_METHOD_SOURCE_FILE) as fms:
                    methodSourceFileData = fms.read()
                    methodSourceFileData = methodSourceFileData.replace(TEMPLATE_HEADER_EXT, includeString)
                    # insert parameter parsing placeholder
                    with open(TEMPLATE_PARSER_SOURCE_FILE) as ptf:
                        parserCode = ptf.read()
                        methodSourceFileData = methodSourceFileData.replace(TEMPLATE_PARSING_ROUTINES, parserCode)

                    stubs = ''
                    # Process collected function declarations in new separate method source file
                    for declaration in self.codeMethodImplementations:
                        stubs += declaration + '\n'
                    methodSourceFileData = methodSourceFileData.replace(TEMPLATE_METHOD_STUBS, stubs)
                    methodSourceFileName = self.methodHeaderPath.replace('.h', '.c')
                    print('Writing to file: {}'.format(methodSourceFileName))
                    with open(methodSourceFileName, 'w') as fms_out:
                        now = datetime.now()
                        methodSourceFileData = methodSourceFileData.replace('CODE_GENERATION_DATE', '{}'.format(now))
                        fms_out.write(methodSourceFileData)
                # Generate Method Header File
                with open(TEMPLATE_METHOD_HEADER_FILE) as fmh:
                    methodHeaderFileData = fmh.read()
                    # Remove 'extern ' from the list we created above, as these are local to this file
                    methodHeaderFileData = methodHeaderFileData.replace(TEMPLATE_METHOD_FORWARDS,
                        codeForwardDeclarations.replace(EXTERN_METHOD_PROTO, ''))
                    methodHeaderFileData = methodHeaderFileData.replace('FILENAME_PLACEHOLDER',
                        self.methodHeaderPath.replace('.h', '').upper())
                    print('Writing to file: {}'.format(self.methodHeaderPath))
                    with open(self.methodHeaderPath, 'w') as fmh_out:
                        now = datetime.now()
                        methodHeaderFileData = methodHeaderFileData.replace('CODE_GENERATION_DATE', '{}'.format(now))
                        fmh_out.write(methodHeaderFileData)
            else:
                # remove header placeholder
                consoleFileData = consoleFileData.replace(TEMPLATE_HEADER_EXT, '')

                # insert parameter parsing placeholder
                with open(TEMPLATE_PARSER_SOURCE_FILE) as ptf:
                    parserCode = ptf.read()
                    consoleFileData = consoleFileData.replace(TEMPLATE_PARSING_ROUTINES, parserCode)

                # Process collected function declarations locally
                for declaration in self.codeMethodImplementations:
                    consoleFileData += declaration + '\n'

            print('Writing to file: {}'.format(self.outputPath))
            with open(self.outputPath, 'w') as fout:
                now = datetime.now()
                consoleFileData = consoleFileData.replace('CODE_GENERATION_DATE', '{}'.format(now))
                fout.write(consoleFileData)

if (__name__ == '__main__' ):
    parser = argparse.ArgumentParser(description='Console Builder')

    parser.add_argument('-i', action='store', dest='inputConfig',
        default='consoleFramework.xml', help='Console Description XML file')

    parser.add_argument('-o', action='store', dest='outputFile',
        default='Console.c', help='Output C source file')

    parser.add_argument('-e', type=str2bool, nargs='?',
        const=True, default=False, dest='externalize',
        help='<Optional flag> Externalize Methods to a separate source file')

    arguments = parser.parse_args()

    print('Starting...')
    foo = genConsole(arguments.inputConfig, arguments.outputFile, arguments.externalize)
    foo.start()
    print('Done')

