from common.handles import LANGUAGE_MODEL



class ArchitectAPI:
    def __init__(self):
        code_dir = LANGUAGE_MODEL.config["code_dir"]
        arch_dir = f"{code_dir}/architecture"
        pass