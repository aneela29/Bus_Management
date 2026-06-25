from flask import Flask, render_template, request, redirect, url_for, session
import backend
import copy

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
        seen_ids = set()
        
        for i in range(len(bus_ids)):
            bus_id_clean = bus_ids[i].strip()
            if bus_id_clean:
                if bus_id_clean in seen_ids:
                    continue 
                seen_ids.add(bus_id_clean)
                
                bus_data.append({
                    'id': bus_id_clean,
                    'arrival': int(arrivals[i]) if arrivals[i] else 0,
                    'boarding': int(boardings[i]) if boardings[i] else 1,
                    'priority': 0 # Initialize default priority value
                })
        
        session['bus_data'] = bus_data
        session.modified = True
        return redirect(url_for('select_algorithm'))
        
    bus_data = session.get('bus_data', [])
    if not isinstance(bus_data, list):
        bus_data = []
        
    return render_template('home.html', bus_data=bus_data)

@app.route('/reset')
def reset():
    session.pop('bus_data', None)
    return redirect(url_for('home'))

@app.route('/select-algorithm')
def select_algorithm():
    bus_data = session.get('bus_data', [])
    total_buses = len(bus_data)
    
    if total_buses == 0:
        recommendation = {
            'best': 'none',
            'badge_color': 'slate',
            'reason': 'No bus fleet configurations found. Please populate terminal schedule data first.',
            'comparisons': {}
        }
        return render_template('select_algorithm.html', recommendation=recommendation)

    # Helper function to simulate a route and calculate its true average turnaround time (tst)
    def calculate_simulation_att(algo_type):
        try:
            sim_data = copy.deepcopy(bus_data)
            if algo_type == 'fcfs':
                results, _ = backend.run_fcfs(sim_data)
            elif algo_type == 'sjf':
                results, _ = backend.run_sjf(sim_data)
            elif algo_type == 'srtf':
                results, _ = backend.run_srtf(sim_data)
            elif algo_type == 'priority':
                results, _ = backend.run_priority(sim_data)
            elif algo_type == 'rr':
                results, _ = backend.run_rr(sim_data, quantum=2)
            
            if results:
                # Total Stay Time (tst) is mathematically identical to Turnaround Time (TAT)
                total_tst = sum(getattr(res, 'total_stay_time', 0) for res in results)
                return total_tst / len(results)
            return 999.0
        except Exception:
            return 999.0

    # Execute simulation and grab true mathematical numbers
    att_fcfs = calculate_simulation_att('fcfs')
    att_sjf = calculate_simulation_att('sjf')
    att_srtf = calculate_simulation_att('srtf')
    att_priority = calculate_simulation_att('priority')
    att_rr = calculate_simulation_att('rr')

    performance_map = {
        'fcfs': {'name': 'FCFS Policy', 'att': round(att_fcfs, 2), 'color': 'blue'},
        'sjf': {'name': 'SJF Dispatch', 'att': round(att_sjf, 2), 'color': 'emerald'},
        'srtf': {'name': 'SRTF Preemptive', 'att': round(att_srtf, 2), 'color': 'purple'},
        'priority': {'name': 'Priority Scheduler', 'att': round(att_priority, 2), 'color': 'amber'},
        'rr': {'name': 'Round Robin', 'att': round(att_rr, 2), 'color': 'pink'}
    }

    best_algo = min(performance_map, key=lambda k: performance_map[k]['att'])
    winning_score = performance_map[best_algo]['att']
    badge_color = performance_map[best_algo]['color']
    
    if winning_score >= 999.0:
        reason = "⚠️ <strong>Simulation Layout Warning:</strong> The underlying algorithm modules did not return operational results datasets."
    else:
        reason = f"📊 <strong>Mathematical Optimization Analysis:</strong> Simulating your queue profile across all models indicates that <strong>{performance_map[best_algo]['name']}</strong> minimizes terminal congestion, yielding an optimal system Average Turnaround Time of <strong>{winning_score} mins</strong>."

    recommendation = {
        'best': best_algo,
        'badge_color': badge_color,
        'reason': reason,
        'comparisons': performance_map
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
            session.modified = True

    results = []
    gantt = []
    
    # Run the real simulation for display view
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
                'priority': getattr(res, 'priority', 0), 
                'dt': res.departure_time,          
                'tst': res.total_stay_time,        
                'wt': res.waiting_time             
            })
        avg_wt = sum(r['wt'] for r in processed_results) / len(processed_results)
        avg_tst = sum(r['tst'] for r in processed_results) / len(processed_results)

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