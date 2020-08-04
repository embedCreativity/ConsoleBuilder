# ConsoleBuilder
XML-based Console Interaction Description to C Source Code Generator

# Description
I tend to write console-based user interfaces for my embedded systems. 
These interfaces have an almost "conversational language" style to signal the user's intention to the system.
As such, writing the source code to parse the user's input to the system is boring and tediously painful. To avoid
writing yet another console user input parser, I've decided it would be better to simply describe the tree-like structure
of the desired console command line interaction possibilities. (e.g., "set led on 1" and similarly "set led off 2")

In this xml-description of an intended command line architecture, the designer documents each step of the way with descriptions,
which are then later used to systematically build dynamic help output when a user enters invalid commands. The help output prints
messages relevant to the stage of input the user is attempting to access (branch of the command tree).

Let's just say, documentation is in the code itself. Clone this repo and run the python script. It will ask you to provide a path to your
XML description file. To start, point it at the one provided in the repo. Notice that in the XML description file, eventually, each "branch"
of the command tree will end in a "method" call. A method has arguments, which have a type and a description of their own. This too is used in
help output if needed.

When the python script executes, it will generate a C source file (for now it's just called foo.c) that you can feel free to move to your own
project repo and modify as needed.

As far as this project, my intention is to only modify the consoleFramework.xml and CommandTreeTemplate.c files, which are both used in the generation
of your foo.c output file. Note that the CommandTreeTemplate.c file is not meant to be compiled as is. There are placeholder words in it that do not
follow proper C syntax. The genConsole.py file replaces these placeholders with generated code in these locations.

Also, the script generates some dummy methods at the end of the output file, so it can be compiled and played with right away, but you should really make
the method prototypes at the beginning of the generated file 'extern' and move the method implementations out to a file of your own creation. 

This project really only automates the creation of the source that recursively parses user input, following the command tree architecture you describe in
the xml description and provides useful help output to the user when they don't get it right. Eventually, whatever the user ends up commanding, the goal is
to have it end up calling one of your methods - and that's on you to write.
