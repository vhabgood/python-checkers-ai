victor@VicNRylee:~/Desktop/checkers/Programs/checkers_project$ python3 -m main 
<frozen importlib._bootstrap>:488: RuntimeWarning: Your system is avx2 capable but pygame was not built with support for it. The performance of some of your blits could be adversely affected. Consider enabling compile time detection with environment variables like PYGAME_DETECT_AVX2=1 if you are compiling without cross compilation.
pygame 2.5.2 (SDL 2.30.0, Python 3.12.3)
Hello from the pygame community. https://www.pygame.org/contribute.html
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/home/victor/Desktop/checkers/Programs/checkers_project/main.py", line 10, in <module>
    from engine.checkers_game import CheckersGame, FPS
  File "/home/victor/Desktop/checkers/Programs/checkers_project/engine/checkers_game.py", line 6, in <module>
    from .board import Board
  File "/home/victor/Desktop/checkers/Programs/checkers_project/engine/board.py", line 4, in <module>
    from .piece import Piece
ModuleNotFoundError: No module named 'engine.piece'

