
def get_args(args):
    args_dict = dict()
    index = 1
    while index < len(args):
        key = args[index]
        value = args[index+1]
        args_dict[key] = value
        index += 2
        
    return args_dict

def get_mandatory_arg(args_dict, key):
    if key in args_dict:
        return args_dict[key]
    else:
        print(f"Missing mandatory argument {key}")
        exit(1)

def get_optional_arg(args_dict, key, default_value):
    if key in args_dict:
        return args_dict[key]
    else:
        return default_value
