#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <ctype.h>
#include <stdbool.h>

// prototype method function pointer
typedef bool (*Method_t)(const char*);

// Structure of a CommandTree Node
typedef struct commandTreeNode_t
{
    const char* name;
    const char* desc;
    const Method_t method;
    const char* argDesc;
    const uint32_t childCount;
    const struct commandTreeNode_t** children;
} commandTreeNode_t;

// method forward declarations
METHOD_FUNC_FORWARD_DECLARATIONS

// common string declarations
STRING_DECLARATIONS

// node declarations
NODE_DECLARATIONS

#define USER_INPUT_BUF_SIZE 128

char userInput[USER_INPUT_BUF_SIZE];
char* ptrUserInput;

/************************************************************************************/
/* Example Parameter Parsing Routines                                               */
/************************************************************************************/
bool getUnsignedDecimal(const char* input, uint32_t* num)
{
    int ret;
    ret = sscanf(input, "%d", num);
    if (ret < 1)
    {
        return false;
    }
    return true;
}

bool getUnsignedHex(const char* input, uint32_t* num)
{
    int ret;
    ret = sscanf(input, "0X%x", num);
    if (ret < 1)
    {
        return false;
    }
    return true;
}

/************************************************************************************/
/* Process user input prior to processing                                           */
/************************************************************************************/
uint32_t sanitizeString(char* input, uint32_t size)
{
    uint32_t i;

    // protect against an idiotic (0-1) error in the for loop below
    if (0 == size)
    {
        return 0;
    }

    for (i = 0; i < (size - 1); i++)
    {
        input[i] = toupper(input[i]);
        // quit and NULL terminate when terminating characters have been identified
        if (('\n' == input[i]) || ('\r' == input[i]) || ('\0' == input[i]))
        {
            break;
        }
    }
    // Always NULL terminate where we quit transforming to uppercase
    input[i] = 0;

    return i;
}

/************************************************************************************/
/* Context-based help menu                                                          */
/************************************************************************************/
void printHelp(const commandTreeNode_t* node)
{
    printf("HELP:\n");
    if (&node1 != node)
    {
        printf("%s - %s\n", node->name, node->desc);
    }

    if (NULL != node->method)
    {
        if (NULL != node->argDesc)
        {
            printf("ARGS:\n  %s\n", node->argDesc);
        }
        else
        {
            printf("ARGS:\nNone\n");
        }
    }
    else
    {
        for (uint32_t i = 0; i < node->childCount; i++)
        {
            printf("  -> %s - %s\n", node->children[i]->name, node->children[i]->desc);
        }
    }
}

/************************************************************************************/
/* Example main()                                                                   */
/************************************************************************************/
int main(void)
{
    uint32_t numChars;
    char* tok;
    const char delim[] = " ";
    const commandTreeNode_t* node = &node1;

    printf("Hello, World!\n");
    while (1)
    {
        // It's a courtesy to provide a command prompt
        printf("->");
        // No matter how you get the user data into a buffer, you should call sanitizeString() on it
        memset(userInput, 0, sizeof(char) * USER_INPUT_BUF_SIZE);
        if (NULL != fgets(userInput, USER_INPUT_BUF_SIZE, stdin))
        {
            numChars = sanitizeString(userInput, USER_INPUT_BUF_SIZE);
        }
        else {
            printf("ERROR - error in capturing user input\n");
            break;
        }
        if (0 == strncmp(userInput, "QUIT", USER_INPUT_BUF_SIZE))
        {
            break;
        }

        // Break up the command sentence into command words
        tok = strtok(userInput, delim);
        while (tok != NULL)
        {
            bool found = false;

            // Check current node for branches matching command word
            for (uint32_t i = 0; i < node->childCount; i++)
            {
                if (0 == strcmp(tok, node->children[i]->name))
                {
                    // update node to point at this new match
                    node = node->children[i];
                    found = true;
                    break;
                }
            }

            // Garbage command found
            if (!found)
            {
                printHelp(node);
                node = &node1; // reset node pointer to root
                break;
            }

            // Check to see if this new node is a method
            if (NULL != node->method)
            {
                char* args = tok;
                uint32_t cmdOffset = strlen(tok);

                // If there's valid data after our command tokenizer, then those are arguments
                bool ret;
                if ('\0' != *(tok + cmdOffset + 1))
                {
                    args += cmdOffset + 1;
                    ret = node->method(args);
                }
                else
                {
                    // verify the method wasn't expecting an argument by looking for an argument description
                    if (NULL != node->argDesc)
                    {
                        ret = false;
                    }
                    else
                    {
                        ret = node->method(NULL);
                    }
                }

                if (!ret)
                {
                    printHelp(node);
                }
                node = &node1; // reset node pointer to root
                break; // abandon remaining string if present
            }
            tok = strtok(NULL, delim);

            // Check if we ran out of input string before a valid command was found
            if (NULL == tok)
            {
                printHelp(node);
                node = &node1; // reset node pointer to root
            }
        } // end input string processing loop
    }

    printf("Goodbye.\n");

    return 0;
}

