from app import app, socketio

if __name__ == '__main__':
    # Run the Remote Interview System on port 5001
    socketio.run(app, host='0.0.0.0', port=5001, debug=True) 