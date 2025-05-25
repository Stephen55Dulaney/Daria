from app import app, socketio

if __name__ == '__main__':
    # Run the Daria Interview Tool on port 5003
    socketio.run(app, host='0.0.0.0', port=5003, debug=True) 