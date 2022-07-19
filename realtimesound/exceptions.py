class InvalidHostName(Exception):
    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return F"There is no audio system named '{self.name}'."
