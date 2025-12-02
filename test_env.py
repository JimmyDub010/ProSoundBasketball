import sys
print("Python version:", sys.version)
try:
    import pygame
    print("Pygame imported:", pygame.ver)
    pygame.init()
    print("Pygame initialized")
except Exception as e:
    print("Pygame error:", e)

try:
    from accessible_output2.outputs.auto import Auto
    print("Accessible Output imported")
    s = Auto()
    print("Speaker initialized")
except Exception as e:
    print("Accessible Output error:", e)
