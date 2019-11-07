import argparse
import time
from enum import Enum

import numpy as np

from udacidrone import Drone
from udacidrone.connection import MavlinkConnection, WebSocketConnection  # noqa: F401
from udacidrone.messaging import MsgID

DEBUG = True

class States(Enum):
    MANUAL = 0
    ARMING = 1
    TAKEOFF = 2
    WAYPOINT = 3
    LANDING = 4
    DISARMING = 5


class BackyardFlyer(Drone):

    def __init__(self, connection):
        super().__init__(connection)
        if DEBUG: 
            print("INITIALIZE")
        self.target_position = np.array([0.0, 0.0, 0.0])
        self.all_waypoints = []
        self.in_mission = True
        self.check_state = {}

        # initial state
        self.flight_state = States.MANUAL

        # TODO: Register all your callbacks here
        self.register_callback(MsgID.LOCAL_POSITION, self.local_position_callback)
        self.register_callback(MsgID.LOCAL_VELOCITY, self.velocity_callback)
        self.register_callback(MsgID.STATE, self.state_callback)

    def local_position_callback(self):
        if DEBUG: 
            print("local_position_callback")

        if self.flight_state == States.TAKEOFF: # if in takeoff state set the waypoints
            if -1.0 * self.local_position[2] > 0.95 * self.target_position[2]:
                self.all_waypoints = self.calculate_box()  # set the way points as soon as we leave the groung
                self.waypoint_transition() # make waypoint transition
        elif self.flight_state == States.WAYPOINT:
            if np.linalg.norm(self.target_position[0:2]-self.local_position[0:2]) < 1.0:
                if len(self.all_waypoints) > 0:
                    self.waypoint_transition()
                else:
                    if np.linalg.norm(self.local_velocity[0:2]) < 1.0: # no more waypoints and we have reached our destination land it
                        self.landing_transition()

    def velocity_callback(self):
        if DEBUG: 
            print("velocity_callback")

        """
        This method is completed

        This triggers when `MsgID.LOCAL_VELOCITY` is received and self.local_velocity contains new data
       
        
        if self.flight_state == States.LANDING:     # if we are landing monitor position to switch to disarming once completed
            if self.global_position[2] - self.global_home[2] < 0.1:
                if abs(self.local_position[2]) < 0.01:
                    self.disarming_transition()
        """
        pass

    def state_callback(self):
        if DEBUG: 
            print("state_callback")
        
        """
        TODO: Implement this method

        This triggers when `MsgID.STATE` is received and self.armed and self.guided contain new data
        """
        # check if we are in mission state we want to control the drone
        if self.in_mission:
            if self.flight_state == States.MANUAL:
                if self.guided:
                    self.flight_state = States.ARMING
            elif self.flight_state == States.ARMING:
                if self.armed:
                    self.takeoff_transition()
            elif self.flight_state == States.LANDING:
                if ~self.armed & ~self.guided:
                    self.stop()
                    self.in_mission = False
            elif self.flight_state == States.DISARMING:
                pass
                    
    def calculate_box(self):
        if DEBUG: 
            print("calculate_box")
        """This method is completed
        
        1. Return waypoints to fly a box
        """
        cp = np.array([self.local_position[0], self.local_position[1], -self.local_position[2]])  # get the current local position -> note we need to change the sign of the down coordinate to be altitude
    
        local_waypoints = [cp + [5.0, 0.0, 3.0], cp + [10.0, 0.0, 3.0], cp + [15.0, 0.0, 3.0], 
                           cp + [15.0, 5.0, 3.0], cp + [15.0, 10.0, 3.0], cp + [15.0, 15.0, 3.0], 
                           cp + [10.0, 15.0, 3.0], cp + [5.0, 15.0, 3.0], cp + [0.0, 15.0, 3.0], 
                           cp + [0.0, 10.0, 3.0], cp + [0.0, 5.0, 3.0], cp + [0.0, 0.0, 3.0]]

        return local_waypoints

    def arming_transition(self):
        print("arming_transition")
        """This method is completed
        
        1. Take control of the drone
        2. Pass an arming command
        3. Set the home location to current position
        4. Transition to the ARMING state
        """
        
        self.take_control()
        self.arm()
        self.set_home_position(self.global_position[0], self.global_position[1],
                               self.global_position[2]) 
        self.flight_state = States.ARMING

    def takeoff_transition(self):
        print("takeoff transition")
        """This method is completed
        
        1. Set target_position altitude to 3.0m
        2. Command a takeoff to 3.0m
        3. Transition to the TAKEOFF state
        """
        target_altitude = 3.0
        self.target_position[2] = target_altitude
        self.takeoff(target_altitude)
        self.flight_state = States.TAKEOFF

    def waypoint_transition(self):
        print("waypoint_transition")
        
        """This method is completed
    
        1. Command the next waypoint position
        2. Transition to WAYPOINT state
        """
        
        self.target_position = self.all_waypoints.pop(0)   # get next waypoint        
        print('target position', self.target_position)     # print next position
        self.cmd_position(self.target_position[0], self.target_position[1], self.target_position[2], 0.0) # send command
        self.flight_state = States.WAYPOINT # set the state

    def landing_transition(self):
        if DEBUG: 
            print("landing_transition")
        """This method is completed
        
        1. Command the drone to land
        2. Transition to the LANDING state
        """
        print("landing transition")
        self.land()
        self.flight_state = States.LANDING

    def disarming_transition(self):
        if DEBUG: 
            print("disarming_transition")
            
        """This method is completed
        
        1. Disarm drone
        2. Release control of the drone
        3. Transition to the DISARMING state
        """

        print("disarm transition")
        self.disarm()
        self.release_control()
        self.flight_state = States.DISARMING

    def manual_transition(self):
        if DEBUG: 
            print("manual_transition")
        """This method is provided
        
        1. Release control of the drone
        2. Stop the connection (and telemetry log)
        3. End the mission
        4. Transition to the MANUAL state
        """
        print("manual transition")

        self.release_control()
        self.stop()
        self.in_mission = False
        self.flight_state = States.MANUAL

    def start(self):
        if DEBUG: 
            print("start")
        """This method is provided
        
        1. Open a log file
        2. Start the drone connection
        3. Close the log file
        """
        print("Creating log file")
        self.start_log("Logs", "NavLog.txt")
        print("starting connection")
        self.connection.start()

        print("Closing log file")
        self.stop_log()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5760, help='Port number')
    parser.add_argument('--host', type=str, default='127.0.0.1', help="host address, i.e. '127.0.0.1'")
    args = parser.parse_args()

    conn = MavlinkConnection('tcp:{0}:{1}'.format(args.host, args.port), threaded=False, PX4=False)
    #conn = WebSocketConnection('ws://{0}:{1}'.format(args.host, args.port))
    drone = BackyardFlyer(conn)
    time.sleep(2)
    drone.start()
