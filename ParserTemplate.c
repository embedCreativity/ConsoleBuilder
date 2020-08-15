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

