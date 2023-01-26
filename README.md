[![FloWide](https://flowide.net/wp-content/uploads/2022/06/fw-logo.svg "Go to FloWide webpage")](https://flowide.net)

# Anchor Distance Map

This application can be run with streamlit on the `FloWide` workbench.

## Functions

At the first run, we can see only a settings panel and the `Calculate` button.

![image](https://user-images.githubusercontent.com/6457941/214871226-d764c2f9-1b3d-476c-bb52-dbb6b9704270.png)

Clicking the `Calculate` button will recalculate all anchor distances.

A warning shows that it can not calculate the positions from the distances yet.


### Settings

On the first line, we can set the translation of the layout. We can select an anchor for the center (0, 0), and an extra translation (x, y).

On the second line, we can select whether the layout is mirrored or not, and an extra rotation argument (0-360).

Later these settings can be replaced with Robi translation script which calculates the rotation matrix and translation array automatically.


![image](https://user-images.githubusercontent.com/6457941/214875871-0343eedc-c6d3-4d6e-b400-4367456489f1.png)


The map shows the anchors. 
- The black circles come from the SCL component, which stores the anchor's real positions. 
- The green circles are the calculated positions.

After the map, 1 or 2 tables will show depending on the SCL's existence which contain the raw positions.
