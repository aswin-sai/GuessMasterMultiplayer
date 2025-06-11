from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
import random
import string
import qrcode
import io
import base64

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app, async_mode="threading")  # Ensure threading mode for local dev

# In-memory game state
games = {}

def generate_room_code(length=5):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_qr_code(url):
    img = qrcode.make(url)
    buf = io.BytesIO()
    # Fix: Use img.save(buf, format='PNG') only if PIL is available, else use img.save(buf)
    try:
        img.save(buf, format='PNG')
    except TypeError:
        img.save(buf)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create')
def create():
    room = generate_room_code()
    number = random.randint(10, 99)
    games[room] = {
        'number': number,
        'players': {},
        'guesses': [],
        'active': True
    }
    public_url = None
    try:
        import requests
        # Try to get the public URL from ngrok's local API (if running)
        ngrok_api = "http://0.0.0.0:4040/api/tunnels"
        tunnels = requests.get(ngrok_api).json()["tunnels"]
        for t in tunnels:
            if t.get("public_url", "").startswith("https"):
                public_url = t["public_url"]
                break
    except Exception:
        public_url = None

    if public_url:
        join_url = f"{public_url}/join/{room}"
    else:
        # fallback to LAN IP (will only work on same network)
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            local_ip = s.getsockname()[0]
        except Exception:
            local_ip = '0.0.0.0'
        finally:
            s.close()
        join_url = f'http://{local_ip}:5000/join/{room}'
    qr_data = generate_qr_code(join_url)
    return render_template('host.html', room=room, qr_data=qr_data, join_url=join_url, public_ip=public_url)

@app.route('/join/<room>')
def join(room):
    # Accept both upper/lowercase room codes
    room = room.upper()
    if room not in games or not games[room]['active']:
        return "Room not found or game ended.", 404
    return render_template('join.html', room=room)

@socketio.on('join_room')
def handle_join(data):
    room = data['room'].upper()
    username = data['username']
    if room not in games or not games[room]['active']:
        emit('error', {'message': 'Room not found or game ended.'})
        disconnect()
        return
    games[room]['players'][request.sid] = username
    join_room(room)
    emit('player_joined', {'username': username, 'players': list(games[room]['players'].values())}, room=room)

@socketio.on('make_guess')
def handle_guess(data):
    room = data['room'].upper()
    guess = int(data['guess'])
    username = games[room]['players'].get(request.sid, 'Unknown')
    number = games[room]['number']
    if not games[room]['active']:
        emit('game_over', {'message': 'Game already ended.'})
        return
    result = ''
    if guess == number:
        result = 'correct'
        games[room]['active'] = False
        emit('guess_result', {'username': username, 'guess': guess, 'result': result}, room=room)
        emit('game_over', {'winner': username, 'number': number}, room=room)
    else:
        if abs(guess - number) <= 2:
            clue = "🔥 Very close!"
        elif guess < number:
            clue = "🔼 Go higher!"
        else:
            clue = "🔽 Go lower!"
        result = 'wrong'
        emit('guess_result', {'username': username, 'guess': guess, 'result': result, 'clue': clue}, room=room)

@socketio.on('disconnect')
def on_disconnect():
    for room, game in games.items():
        if request.sid in game['players']:
            username = game['players'].pop(request.sid)
            emit('player_left', {'username': username, 'players': list(game['players'].values())}, room=room)
            break

if __name__ == '__main__':
    print("To allow access from anywhere, use a tunneling service like ngrok (https://ngrok.com/):")
    print("  1. Run: ngrok http 5000")
    print("  2. Use the public URL shown by ngrok as the join link.")
    print("  3. The QR code will use ngrok if detected, else LAN IP.")
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
