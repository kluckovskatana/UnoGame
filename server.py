import socketio
import eventlet
import random
from eventlet import wsgi
from flask import Flask

sio = socketio.Server(cors_allowed_origins="*")
app = Flask(__name__)

# ===================== Deck & State =====================
numbers = list(range(0, 10))
colors = ["R", "G", "B", "Y"]

def build_deck():
    deck = [f"{num}{color}" for color in colors for num in numbers]
    deck += deck  # duplicate like real UNO
    random.shuffle(deck)
    return deck

game_state = {
    "players": [],       # [{"sid": ..., "name": ..., "hand": [...]}]
    "deck": [],
    "discard": [],       # top card is discard[-1]
    "current_turn": 0,   # index into players list
    "started": False,
    "winner": None,
    # Chain play state
    "chain_number": None,   # number that must match to continue chain
    "has_drawn": False,     # whether current player already drew this turn
}

def deal_hand(n=7):
    hand = []
    for _ in range(n):
        if game_state["deck"]:
            hand.append(game_state["deck"].pop())
    return hand

def get_top_card():
    return game_state["discard"][-1] if game_state["discard"] else None

def can_play(card, top):
    """Card can be played if it shares color or number with top card."""
    if top is None:
        return True
    card_num, card_color = card[:-1], card[-1]
    top_num, top_color = top[:-1], top[-1]
    return card_color == top_color or card_num == top_num

def broadcast_state():
    """Send game state to all players. Each player sees their own hand."""
    top = get_top_card()
    current_player = game_state["players"][game_state["current_turn"]]

    for p in game_state["players"]:
        sio.emit("game_update", {
            "your_hand": p["hand"],
            "top_card": top,
            "current_turn_name": current_player["name"],
            "is_your_turn": p["sid"] == current_player["sid"],
            "players_card_counts": [
                {"name": pl["name"], "count": len(pl["hand"])}
                for pl in game_state["players"]
            ],
            "winner": game_state["winner"],
            "chain_number": game_state["chain_number"],  # None or "5" etc.
            "has_drawn": game_state["has_drawn"],
        }, to=p["sid"])

# ===================== Socket.IO Events =====================
@sio.event
def connect(sid, environ):
    print(f"Connected: {sid}")

@sio.event
def disconnect(sid):
    gs = game_state
    gs["players"] = [p for p in gs["players"] if p["sid"] != sid]
    print(f"Disconnected: {sid}")
    sio.emit("players", [p["name"] for p in gs["players"]])

@sio.event
def join(sid, nickname):
    print(f"{nickname} joined")
    game_state["players"].append({"sid": sid, "name": nickname, "hand": []})
    sio.emit("players", [p["name"] for p in game_state["players"]])

    if len(game_state["players"]) == 2:
        start_game()

def start_game():
    gs = game_state
    gs["deck"] = build_deck()
    gs["discard"] = []
    gs["current_turn"] = 0
    gs["started"] = True
    gs["winner"] = None
    gs["chain_number"] = None
    gs["has_drawn"] = False

    for p in gs["players"]:
        p["hand"] = deal_hand(7)

    # Place first card on discard pile
    gs["discard"].append(gs["deck"].pop())

    print("Game starting! Top card:", get_top_card())
    # Notify players their names/order
    sio.emit("start_game", [p["name"] for p in gs["players"]])
    broadcast_state()

@sio.event
def play_card(sid, card):
    """Player attempts to play a card."""
    gs = game_state
    if gs["winner"]:
        return

    current_player = gs["players"][gs["current_turn"]]
    if current_player["sid"] != sid:
        sio.emit("error_msg", "It's not your turn!", to=sid)
        return

    if card not in current_player["hand"]:
        sio.emit("error_msg", "You don't have that card!", to=sid)
        return

    top = get_top_card()
    card_num = card[:-1]

    # During a chain: only same number allowed
    if gs["chain_number"] is not None:
        if card_num != gs["chain_number"]:
            sio.emit("error_msg", f"Chain active! Must play a {gs['chain_number']} card or end turn.", to=sid)
            return
    else:
        if not can_play(card, top):
            sio.emit("error_msg", f"Can't play {card} on {top}!", to=sid)
            return

    # Valid play — remove card, add to discard
    current_player["hand"].remove(card)
    gs["discard"].append(card)

    # Check win condition
    if len(current_player["hand"]) == 0:
        gs["winner"] = current_player["name"]
        gs["chain_number"] = None
        gs["has_drawn"] = False
        broadcast_state()
        return

    # Check if player still has more cards of the same number → start/continue chain
    same_number_left = any(c[:-1] == card_num for c in current_player["hand"])
    if same_number_left:
        gs["chain_number"] = card_num   # stay in turn, chain active
    else:
        # No more of that number — chain ends, advance turn
        gs["chain_number"] = None
        gs["has_drawn"] = False
        gs["current_turn"] = (gs["current_turn"] + 1) % len(gs["players"])

    broadcast_state()

@sio.event
def end_turn(sid):
    """Player manually ends their turn (skips remaining chain)."""
    gs = game_state
    if gs["winner"]:
        return

    current_player = gs["players"][gs["current_turn"]]
    if current_player["sid"] != sid:
        sio.emit("error_msg", "It's not your turn!", to=sid)
        return

    gs["chain_number"] = None
    gs["has_drawn"] = False
    gs["current_turn"] = (gs["current_turn"] + 1) % len(gs["players"])
    broadcast_state()

@sio.event
def draw_card(sid):
    """Player draws 1 card. Only allowed once per turn. Does NOT auto-end turn."""
    gs = game_state
    if gs["winner"]:
        return

    current_player = gs["players"][gs["current_turn"]]
    if current_player["sid"] != sid:
        sio.emit("error_msg", "It's not your turn!", to=sid)
        return

    if gs["has_drawn"]:
        sio.emit("error_msg", "You already drew a card this turn!", to=sid)
        return

    if gs["chain_number"] is not None:
        sio.emit("error_msg", "Can't draw during a chain! End your turn instead.", to=sid)
        return

    if not gs["deck"]:
        top = gs["discard"].pop()
        gs["deck"] = gs["discard"]
        random.shuffle(gs["deck"])
        gs["discard"] = [top]

    if gs["deck"]:
        card = gs["deck"].pop()
        current_player["hand"].append(card)
        gs["has_drawn"] = True
        print(f"{current_player['name']} drew {card}")

    # Stay in turn — player can now play the drawn card or end turn manually
    broadcast_state()

# ===================== Run Server =====================
if __name__ == "__main__":
    wsgi_app = socketio.WSGIApp(sio, app)
    print("Server running at http://127.0.0.1:5555")
    wsgi.server(eventlet.listen(("0.0.0.0", 5555)), wsgi_app)