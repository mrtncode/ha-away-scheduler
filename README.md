# Home Assistant Away Scheduler

## Plan
- Algorithm for automatic control
-> Sun position/ light, randomness, defined time intervals, status of other devices
- Automatic action calls (to control light, switch, ..)
- Notifications (action calls to notify services + event entity)
- Test mode (quick on and off)

## Details
Global settings:
- min gap between events - example: 10min
- not all devices at the same time - true/ false

Device settings:
- name
- area type

Area settings:
- sunset offset range (time) (approximate)
- duration (long, short, mid, custom)
- randomness level (high, mid, low)
- activity level?
