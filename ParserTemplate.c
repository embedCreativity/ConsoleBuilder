/************************************************************************************/
/* Example Parameter Parsing Routines                                               */
/************************************************************************************/
static bool getSignedDecimal(const char* input, int32_t* num)
{
    int ret;
    ret = sscanf(input, "%d", num);
    if (ret < 1)
    {
        return false;
    }
    return true;
}

static bool getUnsignedHex(const char* input, uint32_t* num)
{
    int ret;
    ret = sscanf(input, "0X%x", num);
    if (ret < 1)
    {
        return false;
    }
    return true;
}
