from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime, timedelta
import os
from groq import Groq
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

# Initialize Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# In-memory data storage with enhanced structure
user_data = {
    'usage': [],
    'goal': None,
    'detox_sessions': [],
    'current_session': None
}

@app.route('/')
def index():
    current_session = user_data.get('current_session')
    time_left = 0
    
    if current_session:
        end_time = current_session['end_time']
        if datetime.now() < end_time:
            time_left = int((end_time - datetime.now()).total_seconds() / 60)
        else:
            user_data['current_session'] = None
    
    return render_template('index.html',
                         goal=user_data['goal'],
                         today_usage=get_today_usage(),
                         yesterday_usage=get_yesterday_usage(),
                         time_left=time_left)

@app.route('/set_goal', methods=['POST'])
def set_goal():
    try:
        minutes = int(request.form.get('goal', 0))
        if minutes > 0:
            user_data['goal'] = minutes
            return jsonify({
                'success': True,
                'goal': minutes
            })
    except ValueError:
        pass
    return jsonify({
        'success': False,
        'error': 'Invalid goal value'
    })

@app.route('/start_detox', methods=['POST'])
def start_detox():
    try:
        duration = int(request.form.get('duration', 0))
        if duration > 0:
            end_time = datetime.now() + timedelta(minutes=duration)
            user_data['current_session'] = {
                'start_time': datetime.now(),
                'end_time': end_time,
                'duration': duration
            }
            return jsonify({
                'success': True,
                'timeLeft': duration
            })
    except ValueError:
        pass
    return jsonify({
        'success': False,
        'error': 'Invalid duration'
    })

@app.route('/log_usage', methods=['GET', 'POST'])
def log_usage():
    if request.method == 'POST':
        try:
            minutes = int(request.form.get('usage', 0))
            if minutes > 0:
                user_data['usage'].append({
                    'timestamp': datetime.now(),
                    'minutes': minutes
                })
                
                # Get AI analysis of usage
                prompt = f"""
                The user spent {minutes} minutes on social media today.
                Their daily goal is {user_data['goal'] if user_data['goal'] else 'not set'} minutes.
                Please provide a brief, encouraging analysis of this usage with one specific actionable tip.
                Keep the response under 2 sentences and maintain a positive tone.
                """
                
                chat_completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt.strip()}],
                    model="llama3-8b-8192",
                    temperature=0.7,
                    max_tokens=100
                )
                analysis = chat_completion.choices[0].message.content
                
                return jsonify({
                    'success': True,
                    'analysis': analysis
                })
        except ValueError:
            pass
        return jsonify({
            'success': False,
            'error': 'Invalid usage value'
        })
    return render_template('log_usage.html')

@app.route('/need_motivation', methods=['GET', 'POST'])
def need_motivation():
    if request.method == 'POST':
        question = request.form.get('question', '').strip()
        if question:
            prompt = f"""
            Question about digital wellness: "{question}"
            Please provide a helpful response that is:
            1. Specific and actionable
            2. Related to digital wellbeing
            3. Limited to 2-3 sentences
            4. Encouraging and practical
            """
            
            try:
                chat_completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": prompt.strip()}],
                    model="llama3-8b-8192",
                    temperature=0.7,
                    max_tokens=150
                )
                response = chat_completion.choices[0].message.content
                
                return jsonify({
                    'success': True,
                    'response': response
                })
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                })
    return render_template('need_motivation.html')

def get_today_usage():
    today = datetime.now().date()
    return sum(
        entry['minutes'] for entry in user_data['usage']
        if 'minutes' in entry and entry['timestamp'].date() == today
    )

def get_yesterday_usage():
    yesterday = (datetime.now() - timedelta(days=1)).date()
    return sum(
        entry['minutes'] for entry in user_data['usage']
        if 'minutes' in entry and entry['timestamp'].date() == yesterday
    )

@app.route('/check_timer')
def check_timer():
    """Endpoint to check remaining time in current detox session"""
    current_session = user_data.get('current_session')
    if current_session:
        now = datetime.now()
        if now < current_session['end_time']:
            minutes_left = int((current_session['end_time'] - now).total_seconds() / 60)
            return jsonify({
                'success': True,
                'timeLeft': minutes_left
            })
    return jsonify({
        'success': False,
        'timeLeft': 0
    })

if __name__ == '__main__':
    app.run(debug=True, port=5001) 