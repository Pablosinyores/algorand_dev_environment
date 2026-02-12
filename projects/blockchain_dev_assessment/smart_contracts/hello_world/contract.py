from algopy import ARC4Contract, BoxMap, Bytes, GlobalState, String, UInt64, op
from algopy.arc4 import abimethod


class HelloWorld(ARC4Contract):
    def __init__(self) -> None:
        self.greeting_counter = GlobalState(UInt64(0), key=b"counter")
        self.greetings = BoxMap(Bytes, String, key_prefix=b"")

    @abimethod()
    def hello(self, name: String) -> String:
        current_count = self.greeting_counter.value
        greeting = "Hello, " + name

        # Box key: name_bytes + "_" + itob(counter)
        # e.g. b"Alice_\x00\x00\x00\x00\x00\x00\x00\x00" for counter=0
        box_key = name.bytes + Bytes(b"_") + op.itob(current_count)
        self.greetings[box_key] = greeting

        self.greeting_counter.value = current_count + UInt64(1)
        return greeting
