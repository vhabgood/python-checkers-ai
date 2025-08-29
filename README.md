This program is designed by Victor Habgood. The purpose is to create an intelligent program that can help advanced and beginning players to learn advanced patterns and other techniques in the game to improve. Improving the game play in real checkers is a good thing for the game. Also, being able to play again a strong AI with some of the most unique and sophisticated abilities in the world is really fun. We will continue to make this better. If you have ideas, feel free to send them vhabgood@gmail.com. 
Project Structure: 
Command to run program for me: python3 -m main (--debug-board) (--no-db)  #debug sends debugging text file to the /logs/ directory after run. #no-db lets you load the game faster without big databases.
__pycache__  __init__.py  constants.py   board.py
victor@VicNRylee:~/Desktop/checkers/Programs/checkers_project$ ls -r *
main.py           CheckersProgramStructure.txt
game_states.py    2025-08-21_14-39-41_checkers_debug.log
game.pdn          2025-08-21_14-34-47_checkers_debug.log
clean_history.sh

tools:
zobrist_generator.py        endgame_generator_3Kv1K1M.py
__init__.py                 endgame_generator_3K1Mv3K.py
endgame_generator.py        endgame_generator_2Kv1M.py
endgame_generator_4Kv3K.py  endgame_generator_2K1Mv3K.py
endgame_generator_4Kv2K.py  endgame_generator_2K1Mv2K.py
endgame_generator_3Kv3K.py  endgame_generator_2K1Mv2K1M.py
endgame_generator_3Kv2K.py  custom_book_generator.py
endgame_generator_3Kv1K.py

resources:
game_resources.pkl  db_3v2_kings.pkl  db_2v1_kings.pkl     custom_book.pkl
db_4v3_kings.pkl    db_3v1_kings.pkl  db_2k1m_vs_3k.pkl    crown.png
db_4v2_kings.pkl    db_3v1k1m.pkl     db_2k1m_vs_2k.pkl
db_3v3_kings.pkl    db_2v1_men.pkl    db_2k1m_vs_2k1m.pkl

__pycache__:
main.cpython-312.pyc  game_states.cpython-312.pyc

logs:
2025-08-29_09-09-10_checkers_debug.log  2025-08-29_09-00-02_checkers_debug.log
2025-08-29_09-06-24_checkers_debug.log

engine:
search.py    piece.py     evaluation.py  checkers_game.py
__pycache__  __init__.py  constants.py   board.py
