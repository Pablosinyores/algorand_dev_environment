from algopy import ARC4Contract, Box, String
from algopy.arc4 import abimethod


class HelloWorld(ARC4Contract):
    def __init__(self) -> None:
        self.greeting = Box(String, key=b"greeting")

    @abimethod()
    def hello(self, name: String) -> String:
        greeting = "Hello, " + name
        self.greeting.value = greeting
        return greeting
