# app.py
from flask import Flask, render_template, request, redirect, url_for, session
import backend

app = Flask(__name__)
app.secret_key = "iiuc_bus_scheduler_super_secret_key"

@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/home', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        bus_ids = request.form.getlist('bus_id[]')
        arrivals = request.form.getlist('arrival_time[]')
        boardings = request.form.getlist('boarding_time[]')
        
        bus_data = []
        for i in range(len(bus_ids)):
            if bus_ids[i].strip():
                bus_data.append({
                    'id': bus_ids[i],
                    'arrival': int(arrivals[i]),
                    'boarding': int(boardings[i])
                })
        
        session['bus_data'] = bus_data
        return redirect(url_for('select_algorithm'))
        
    return render_template('home.html')

@app.route('/reset')
def reset():
    session.pop('bus_data', None)
    return redirect(url_for('home'))

@app.route('/select-algorithm')
def select_algorithm():
    if 'bus_data' not in session:
        return redirect(url_for('home'))
        
    bus_data = session['bus_data']
    total_buses = len(bus_data)
    
    short_boarding_count = sum(1 for b in bus_data if b['boarding'] <= 3)
    long_boarding_count = sum(1 for b in bus_data if b['boarding'] >= 7)
    
    best_algo = "fcfs"
    reason = "Your schedule has uniform, standard boarding patterns. FCFS will handle this sequentially without issues."
    badge_color = "blue"
    
    if total_buses > 1:
        sorted_by_arrival = sorted(bus_data, key=lambda x: x['arrival'])
        if sorted_by_arrival[0]['boarding'] >= 6 and short_boarding_count >= 1:
            best_algo = "srtf"
            badge_color = "purple"
            reason = "🚨 <strong>Convoy Hazard Detected!</strong> Your first bus has a very long boarding time, which will cause massive delays for faster buses behind it under standard lines. Preemptive scheduling (SRTF) is highly recommended to let short-stay buses bypass the queue."
        elif short_boarding_count > long_boarding_count:
            best_algo = "sjf"
            badge_color = "emerald"
            reason = "⚡ <strong>High Turnover Opportunity!</strong> You have several small shuttles/vans with short boarding times. Prioritizing them via Shortest Job First (SJF) will empty the terminal gates in record time."
        elif long_boarding_count >= (total_buses / 2):
            best_algo = "rr"
            badge_color = "pink"
            reason = "⏳ <strong>Heavy Traffic Congestion Risk!</strong> Multiple heavy intercity buses are competing for the bay. Round Robin will prevent gate monopolies by giving everyone a strict time limit (Quantum)."
            
    recommendation = {
        'best': best_algo,
        'badge_color': badge_color,
        'reason': reason
    }
    
    return render_template('select_algorithm.html', recommendation=recommendation)

@app.route('/dashboard/<algo>', methods=['GET', 'POST'])
def dashboard(algo):
    if 'bus_data' not in session:
        return redirect(url_for('home'))
        
    bus_data = session['bus_data']
    quantum = 2
    
    if request.method == 'POST':
        if algo == 'rr':
            quantum = int(request.form.get('quantum', 2))
        elif algo == 'priority':
            for b in bus_data:
                prio_val = request.form.get(f"priority_{b['id']}", 0)
                b['priority'] = int(prio_val)
            session['bus_data'] = bus_data

    results = []
    gantt = []
    
    # backend.py এর সাথে কানেকশন
    if algo == 'fcfs':
        results, gantt = backend.run_fcfs(bus_data)
    elif algo == 'sjf':
        results, gantt = backend.run_sjf(bus_data)
    elif algo == 'srtf':
        results, gantt = backend.run_srtf(bus_data)
    elif algo == 'priority':
        results, gantt = backend.run_priority(bus_data)
    elif algo == 'rr':
        results, gantt = backend.run_rr(bus_data, quantum)

    processed_results = []
    avg_wt = 0
    avg_tst = 0
    
    if results:
        for res in results:
            processed_results.append({
                'id': res.bus_id,
                'arrival': res.arrival_time,
                'boarding': res.boarding_time,      
                'priority': getattr(res, 'priority', 0), # এরর হ্যান্ডেল করার জন্য নিরাপদ মেথড
                'dt': res.departure_time,          
                'tst': res.total_stay_time,        
                'wt': res.waiting_time             
            })
        avg_wt = sum(r['wt'] for r in processed_results) / len(processed_results)
        avg_tst = sum(r['tst'] for r in processed_results) / len(processed_results)

    # ডাইনামিক অপারেশনাল ইনসাইট কল
    operational_insights = backend.get_operational_insights(
        algo=algo, 
        results=results, 
        avg_wt=round(avg_wt, 2), 
        avg_tst=round(avg_tst, 2), 
        quantum=quantum
    )

    descriptions = {
        'fcfs': "First-Come, First-Served: A fair terminal where buses depart strictly based on who registered first. Best used for steady, uniform traffic configurations.",
        'sjf': "Shortest Job First: The dispatcher checks all waiting buses and releases the one with the quickest boarding time first. This clears the gate lanes incredibly fast.",
        'srtf': "Shortest Remaining Time First: A high-stakes system! If a fast-boarding express van arrives while a heavy commuter bus is loading at the gate, the heavy bus is forced back into line.",
        'priority': "Priority Scheduling: VIP routes take center stage. Emergency shuttles, airport expresses, or long-distance intercity liners go straight to the front of the line.",
        'rr': "Round Robin: Absolute fairness. Every bus gets an identical time slice (Max Bay Limit) at the departure bay. If your time expires, you must circle the block."
    }

    return render_template('dashboard.html', 
                           algo=algo, 
                           description=descriptions.get(algo, ""),
                           results=processed_results, 
                           gantt=gantt,
                           avg_wt=round(avg_wt, 2),
                           avg_tst=round(avg_tst, 2), 
                           quantum=quantum,
                           insights=operational_insights)

if __name__ == '__main__':
    app.run(debug=True)