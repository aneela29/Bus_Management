# backend.py

class Bus:
    def __init__(self, bus_id, arrival_time, boarding_time, priority=0):
        self.bus_id = bus_id
        self.arrival_time = arrival_time            # টার্মিনালে আসার সময়
        self.boarding_time = boarding_time          # যাত্রী উঠার সময় (আগে ছিল burst_time)
        self.priority = priority
        self.remaining_boarding_time = boarding_time # বাকি থাকা বোর্ডিং সময়
        self.start_loading_time = -1                # কখন যাত্রী উঠানো শুরু হলো
        self.departure_time = 0                     # টার্মিনাল ছাড়ার সময় (completion_time)
        self.waiting_time = 0                       # অলস দাঁড়িয়ে থাকার সময় (waiting_time)
        self.total_stay_time = 0                    # মোট টার্মিনালে কাটানো সময় (turnaround_time)

def calculate_metrics(buses):
    for bus in buses:
        # Total Stay = Departure Time - Arrival Time
        bus.total_stay_time = bus.departure_time - bus.arrival_time
        # Waiting Time = Total Stay - Boarding Time
        bus.waiting_time = bus.total_stay_time - bus.boarding_time
    return buses

def run_fcfs(bus_data):
    buses = [Bus(b['id'], b['arrival'], b['boarding']) for b in bus_data]
    buses.sort(key=lambda x: x.arrival_time)
    
    current_time = 0
    gantt_chart = []
    
    for bus in buses:
        if current_time < bus.arrival_time:
            current_time = bus.arrival_time
        
        bus.start_loading_time = current_time
        gantt_chart.append({
            "bus_id": bus.bus_id,
            "start": current_time,
            "end": current_time + bus.boarding_time
        })
        current_time += bus.boarding_time
        bus.departure_time = current_time
        
    return calculate_metrics(buses), gantt_chart

def run_sjf(bus_data):
    buses = [Bus(b['id'], b['arrival'], b['boarding']) for b in bus_data]
    current_time = 0
    completed = 0
    n = len(buses)
    gantt_chart = []
    is_completed = [False] * n
    
    while completed != n:
        idx = -1
        min_boarding = float('inf')
        
        for i in range(n):
            if buses[i].arrival_time <= current_time and not is_completed[i]:
                if buses[i].boarding_time < min_boarding:
                    min_boarding = buses[i].boarding_time
                    idx = i
                elif buses[i].boarding_time == min_boarding:
                    if buses[i].arrival_time < buses[idx].arrival_time:
                        idx = i
                        
        if idx != -1:
            bus = buses[idx]
            if current_time < bus.arrival_time:
                current_time = bus.arrival_time
            
            gantt_chart.append({
                "bus_id": bus.bus_id,
                "start": current_time,
                "end": current_time + bus.boarding_time
            })
            current_time += bus.boarding_time
            bus.departure_time = current_time
            is_completed[idx] = True
            completed += 1
        else:
            current_time += 1
            
    return calculate_metrics(buses), gantt_chart

def run_srtf(bus_data):
    buses = [Bus(b['id'], b['arrival'], b['boarding']) for b in bus_data]
    current_time = 0
    completed = 0
    n = len(buses)
    gantt_chart = []
    prev_bus_id = None
    segment_start = 0
    
    while completed != n:
        idx = -1
        min_remaining = float('inf')
        
        for i in range(n):
            if buses[i].arrival_time <= current_time and buses[i].remaining_boarding_time > 0:
                if buses[i].remaining_boarding_time < min_remaining:
                    min_remaining = buses[i].remaining_boarding_time
                    idx = i
        
        if idx != -1:
            if prev_bus_id is not None and prev_bus_id != buses[idx].bus_id:
                gantt_chart.append({"bus_id": prev_bus_id, "start": segment_start, "end": current_time})
                segment_start = current_time
            
            if prev_bus_id is None:
                segment_start = current_time
                
            prev_bus_id = buses[idx].bus_id
            buses[idx].remaining_boarding_time -= 1
            current_time += 1
            
            if buses[idx].remaining_boarding_time == 0:
                buses[idx].departure_time = current_time
                completed += 1
                gantt_chart.append({"bus_id": prev_bus_id, "start": segment_start, "end": current_time})
                prev_bus_id = None
        else:
            if prev_bus_id is not None:
                gantt_chart.append({"bus_id": prev_bus_id, "start": segment_start, "end": current_time})
                prev_bus_id = None
            current_time += 1
            
    merged_gantt = []
    for block in gantt_chart:
        if merged_gantt and merged_gantt[-1]['bus_id'] == block['bus_id'] and merged_gantt[-1]['end'] == block['start']:
            merged_gantt[-1]['end'] = block['end']
        else:
            merged_gantt.append(block)
            
    return calculate_metrics(buses), merged_gantt

def run_priority(bus_data):
    buses = [Bus(b['id'], b['arrival'], b['boarding'], b.get('priority', 0)) for b in bus_data]
    current_time = 0
    completed = 0
    n = len(buses)
    gantt_chart = []
    is_completed = [False] * n
    
    while completed != n:
        idx = -1
        highest_priority = float('inf')
        
        for i in range(n):
            if buses[i].arrival_time <= current_time and not is_completed[i]:
                if buses[i].priority < highest_priority:
                    highest_priority = buses[i].priority
                    idx = i
                elif buses[i].priority == highest_priority:
                    if buses[i].arrival_time < buses[idx].arrival_time:
                        idx = i
                        
        if idx != -1:
            bus = buses[idx]
            gantt_chart.append({
                "bus_id": bus.bus_id,
                "start": current_time,
                "end": current_time + bus.boarding_time
            })
            current_time += bus.boarding_time
            bus.departure_time = current_time
            is_completed[idx] = True
            completed += 1
        else:
            current_time += 1
            
    return calculate_metrics(buses), gantt_chart

def run_rr(bus_data, quantum):
    buses = [Bus(b['id'], b['arrival'], b['boarding']) for b in bus_data]
    buses.sort(key=lambda x: x.arrival_time)
    
    current_time = 0
    queue = []
    gantt_chart = []
    ready_set = set()
    
    if buses:
        queue.append(buses[0])
        ready_set.add(buses[0].bus_id)
        current_time = buses[0].arrival_time
        
    completed = 0
    n = len(buses)
    
    while completed < n:
        if not queue:
            unvisited = [b for b in buses if b.remaining_boarding_time > 0 and b.bus_id not in ready_set]
            if unvisited:
                next_bus = min(unvisited, key=lambda x: x.arrival_time)
                current_time = next_bus.arrival_time
                queue.append(next_bus)
                ready_set.add(next_bus.bus_id)
            else:
                break
                
        current_bus = queue.pop(0)
        take_time = min(current_bus.remaining_boarding_time, quantum)
        
        gantt_chart.append({
            "bus_id": current_bus.bus_id,
            "start": current_time,
            "end": current_time + take_time
        })
        
        current_time += take_time
        current_bus.remaining_boarding_time -= take_time
        
        for b in buses:
            if b.arrival_time <= current_time and b.remaining_boarding_time > 0 and b.bus_id not in ready_set:
                queue.append(b)
                ready_set.add(b.bus_id)
                
        if current_bus.remaining_boarding_time > 0:
            queue.append(current_bus)
        else:
            current_bus.departure_time = current_time
            completed += 1
            
    return calculate_metrics(buses), gantt_chart
def get_operational_insights(algo, results, avg_wt, avg_tst, quantum=2):
    """
    পিওর ম্যাথমেটিক্যাল ডেটার ওপর ভিত্তি করে অ্যালগরিদমের কার্যকারিতা, 
    দুর্বলতা এবং পরবর্তী করণীয় পরামর্শ তৈরি করার ইঞ্জিন।
    """
    insights = {
        'verdict_title': '',
        'verdict_status': '',  # Optimal, Sub-Optimal, Critical
        'weakness': '',
        'actionable_strategy': ''
    }
    
    # ইনপুট বাসের সংখ্যা
    total_buses = len(results)
    if total_buses == 0:
        return insights

    # কনটেক্সট বের করার জন্য শর্ট ও লং বাসের সংখ্যা কাউন্ট করা
    short_buses = sum(1 for b in results if b.boarding_time <= 3)
    long_buses = sum(1 for b in results if b.boarding_time >= 7)
    
    # ১. FCFS এর জন্য অ্যানালাইসিস
    if algo == 'fcfs':
        # যদি কোনো লম্বা বাস আগে এসে শর্ট বাসকে আটকে দেয় (Convoy Effect)
        convoy_detected = False
        if total_buses > 1:
            sorted_by_arrival = sorted(results, key=lambda x: x.arrival_time)
            if sorted_by_arrival[0].boarding_time >= 6 and any(b.boarding_time <= 3 for b in sorted_by_arrival[1:]):
                convoy_detected = True
                
        if convoy_detected:
            insights['verdict_title'] = "Severe Convoy Effect Detected"
            insights['verdict_status'] = "Critical Delay"
            insights['weakness'] = "A heavy, long-boarding bus arrived first and completely blocked shorter, faster buses behind it."
            insights['actionable_strategy'] = "Switch to 'SJF' or 'SRTF' immediately. This will bypass the heavy bus, allowing smaller buses to clear the platforms instantly and drop average waiting delay."
        else:
            insights['verdict_title'] = "Basic Sequential Dispatch"
            insights['verdict_status'] = "Sub-Optimal"
            insights['weakness'] = "Strictly non-preemptive. Does not consider boarding speed or passenger volume, risking unnecessary gate idle times."
            insights['actionable_strategy'] = "If passenger traffic spikes or mixed bus sizes arrive, shift to 'Round Robin' to ensure fair lane distribution."

    # ২. SJF এর জন্য অ্যানালাইসিস
    elif algo == 'sjf':
        insights['verdict_title'] = "High Platform Throughput"
        insights['verdict_status'] = "Optimal Speed"
        insights['weakness'] = "Starvation Risk! Long-route/intercity buses are constantly pushed to the back of the queue if small vans keep arriving."
        insights['actionable_strategy'] = "To prevent long-route operators from protesting, switch to 'Priority Scheduling' and assign high-priority ranks to delayed intercity liners."

    # ৩. SRTF এর জন্য অ্যানালাইসিস
    elif algo == 'srtf':
        insights['verdict_title'] = "Absolute Minimum Wait Time"
        insights['verdict_status'] = "Maximum Efficiency"
        insights['weakness'] = "High Preemption Overhead. Buses are repeatedly forced to halt their loading halfway to clear the gate for incoming faster vans."
        insights['actionable_strategy'] = "While mathematically fastest, pulling buses out of bays repeatedly confuses boarding passengers. Ensure your digital platform signage updates instantly, or switch to 'Round Robin' for predictable time slots."

    # ৪. Priority এর জন্য অ্যানালাইসিস
    elif algo == 'priority':
        insights['verdict_title'] = "VIP Route Enforcement"
        insights['verdict_status'] = "Policy Driven"
        insights['weakness'] = "Low-priority commuter or local buses can face indefinite delays if higher-priority VIP express buses keep arriving at the gate."
        insights['actionable_strategy'] = f"Current Average Delay is {avg_wt} mins. If local lane queues exceed 4 buses, temporarily implement an 'Aging Factor' (manually increase priority of waiting local buses) to clear the backlog."

    # ৫. Round Robin (RR) এর জন্য অ্যানালাইসিস
    elif algo == 'rr':
        if quantum <= 2:
            insights['verdict_title'] = "Rapid Multi-Lane Rotation"
            insights['verdict_status'] = "Highly Fair"
            insights['weakness'] = "Frequent Bay Evictions. Buses are forced to turn around and re-enter the lane too often, wasting physical positioning time at the terminal gate."
            insights['actionable_strategy'] = f"The Max Bay Stay Limit ({quantum} mins) is too restrictive for your fleet. Increase the time limit to 4-5 minutes to allow medium-sized buses to finish boarding in a single cycle."
        else:
            insights['verdict_title'] = "Sluggish Fair Rotation"
            insights['verdict_status'] = "Sub-Optimal"
            insights['weakness'] = f"Large Quantum Defect. A time limit of {quantum} mins is too high; it forces fast buses to wait too long, making the terminal behave like inefficient FCFS."
            insights['actionable_strategy'] = "Reduce the Max Bay Stay Limit to 2 or 3 minutes. This will break heavy boarding monopolies and speed up the cycle rotation for empty slots."

    return insights