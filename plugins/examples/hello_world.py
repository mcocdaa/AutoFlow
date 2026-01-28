class HelloWorldPlugin:
    """
    A simple example plugin that prints Hello World.
    """

    def __init__(self):
        self.name = "Hello World Plugin"
        self.version = "1.0.0"

    def execute(self, name: str = "World"):
        return f"Hello, {name} from AutoFlow!"

def register():
    return HelloWorldPlugin()
