import pydantic


class HelloWorldResponse(pydantic.BaseModel):
    def __init__(self, message: str):
        self.times_greeted = 0
        self.message = message

    def __eq__(self, other):
        return self.message == other.message

    def __repr__(self):
        return f"HelloWorldResponse(message={self.message})"

    def greet(self):
        self.times_greeted += 1
        return self.message
