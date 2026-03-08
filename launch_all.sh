#!/bin/bash

# ============================================================
#  ROS2 Full Stack Launcher — articubot_one
# ============================================================

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${GREEN}[LAUNCHER]${NC} $1"; }
warn() { echo -e "${YELLOW}[WAIT]${NC} $1"; }

PIDS=()
cleanup() {
    echo -e "\n${YELLOW}Shutting down all nodes...${NC}"
    for pid in "${PIDS[@]}"; do
        kill "$pid" 2>/dev/null
    done
    wait
    echo "Done."
    exit 0
}
trap cleanup SIGINT SIGTERM

# ── T1: Gazebo ───────────────────────────────────────────────
log "T1 → Starting Gazebo simulation..."
gnome-terminal --tab --title="T1 Gazebo" -- bash -c \
    "cd /home/p/my_robot_ws && source install/setup.bash && \
     ros2 launch my_bot launch_sim.launch.py; exec bash" &
PIDS+=($!)

warn "Waiting 10s for Gazebo to come up..."
sleep 10

# ── T2: Nav2 ─────────────────────────────────────────────────
log "T2 → Starting Nav2..."
gnome-terminal --tab --title="T2 Nav2" -- bash -c \
    "cd /home/p/my_robot_ws && source install/setup.bash && \
     ros2 launch my_bot navigation.launch.py; exec bash" &
PIDS+=($!)

warn "Waiting 10s for Nav2 to initialise..."
sleep 10

# ── T3: Twist Mux ────────────────────────────────────────────
log "T3 → Starting Twist Mux..."
gnome-terminal --tab --title="T3 TwistMux" -- bash -c \
    "cd /home/p/my_robot_ws && source install/setup.bash && \
     ros2 run twist_mux twist_mux --ros-args \
     --params-file ./src/my_bot/config/twist_mux.yaml \
     -r cmd_vel_out:=cmd_vel; exec bash" &
PIDS+=($!)
sleep 3

# ── T4: RViz2 ────────────────────────────────────────────────
log "T4 → Starting RViz2..."
gnome-terminal --tab --title="T4 RViz2" -- bash -c \
    "cd /home/p/my_robot_ws && source install/setup.bash && \
     rviz2; exec bash" &
PIDS+=($!)
sleep 5

# ── T5: full_teleop.py ───────────────────────────────────────
log "T5 → Starting full_teleop.py..."
gnome-terminal --tab --title="T5 Teleop" -- bash -c \
    "cd /home/p/my_robot_ws && source install/setup.bash && \
     python3 full_teleop.py; exec bash" &
PIDS+=($!)
sleep 2

# ── T6: Follow Waypoints ─────────────────────────────────────
log "T6 -> Sending waypoint goals..."
gnome-terminal --tab --title="T6 NavGoal" -- bash -c \
    "cd /home/p/my_robot_ws && source install/setup.bash && \
     ros2 action send_goal /follow_waypoints nav2_msgs/action/FollowWaypoints \
     \"{poses: [
       {header: {frame_id: 'map'}, pose: {position: {x: -1.02882, y: 4.53283, z: 0.0}, orientation: {z: -0.999854, w: 0.0170975}}},
       {header: {frame_id: 'map'}, pose: {position: {x: -0.255758, y: 1.14174, z: 0.0}, orientation: {z: 0.988939, w: 0.148322}}},
       {header: {frame_id: 'map'}, pose: {position: {x: 2.81291, y: -2.71484, z: 0.0}, orientation: {z: -0.690158, w: 0.723659}}}
     ]}\"; \
     exec bash" &
PIDS+=($!)
sleep 2

log "✅ All nodes launched!"
echo ""
echo -e "${CYAN}Press Ctrl+C to stop everything.${NC}"

wait
