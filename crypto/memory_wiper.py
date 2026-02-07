import ctypes
import sys

class MemoryWiper:
    @staticmethod
    def overwrite_object(obj):
        """
        Attempts to overwrite the memory of a bytearray or mutable object.
        Python immutable strings/bytes cannot be overwritten in place easily.
        We rely on the garbage collector for those, but this helper 
        is for any mutable buffers we might use.
        """
        if isinstance(obj, bytearray):
            for i in range(len(obj)):
                obj[i] = 0
        elif isinstance(obj, list):
             for i in range(len(obj)):
                 obj[i] = None
    
    @staticmethod
    def force_gc():
        import gc
        gc.collect()
