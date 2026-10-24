# stardew_game.py
"""
Điểm khởi chạy tương thích cho trò chơi FarmBot Town (từ gói mô-đun `game/`).
Cách chạy:
    python stardew_game.py
"""

from game.app import FarmBotTownGame, main

__all__ = ["FarmBotTownGame", "main"]

if __name__ == "__main__":
    main()
