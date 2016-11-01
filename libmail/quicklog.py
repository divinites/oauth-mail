FLAG = "Gmail "
PROMPT = ">>> "


class QuickLog:

    @staticmethod
    def log(console_str):
        print(FLAG + PROMPT + console_str)
