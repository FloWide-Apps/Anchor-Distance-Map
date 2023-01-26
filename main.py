import streamlit as st
import requests
from typing import Optional, Mapping
from time import sleep
import pandas as pd
import numpy as np
from sklearn.manifold import MDS
from scipy.spatial import ConvexHull
from collections import OrderedDict
from matplotlib import pyplot as plt
from itertools import pairwise
import statistics


# ############## CONFIGURATION ################
BDCL = 'http://bdcl'
SCL = 'http://scl'
MAX_RETRY = 3  # maximum number of TWR measurement retries
MEAS_COUNT = 5  # measurement averaging number (>=1)
# #############################################

st.set_page_config(layout="wide")


def get(api_ep: str) -> object:
    return requests.get(f'{BDCL}{api_ep}').json()


def put(api_ep: str, val: object) -> object:
    return requests.put(f'{BDCL}{api_ep}', json=val).status_code


def get_variable(anchor_id: int, variable: str) -> object:
    return get(f'/devs/anchors/{anchor_id}/variables/{variable}')


def set_variable(anchor_id: int, variable: str, value: object) -> bool:
    code = put(f'/devs/anchors/{anchor_id}/variables/{variable}', value)
    return 200 <= code < 300


@st.experimental_memo
def get_anchors() -> Mapping[int, int]:
    return {e['uniqueId']: e['lolanIds'][0] for e in get('/devs/anchors')}


anchors = get_anchors()

try:
    scl_anchor_url = f'{SCL}/anchors?limit={max(len(anchors), 25)*2}'
    anchor_pos = {i['devId']: tuple(map(lambda v: v*1000, i["position"]))
                  for i in requests.get(scl_anchor_url).json()}
except Exception:
    anchor_pos = {}


def measure_distance(from_uid: int, to_lid: int) -> Optional[int]:
    summarize = 0
    success_count = 0
    for _ in range(MEAS_COUNT):
        for _ in range(MAX_RETRY):
            if set_variable(from_uid, 'control.perform_twr', to_lid):
                # we need to wait for the twr happening.
                sleep(0.05)
                var = get_variable(from_uid, 'status.twr.result1')
                if isinstance(var, int) and var > 0:
                    summarize += var
                    success_count += 1
                    break
            else:
                # if something went wrong, we must to sleep
                sleep(0.1)

    return summarize // success_count if success_count != 0 else None


@st.experimental_singleton
def get_anchor_distances():
    return OrderedDict()


distances = get_anchor_distances()

to_modifiers = st.container()
to_plot = st.empty()
to_table = st.empty()
to_data = st.empty()


def print_table():
    dists = pd.DataFrame(distances).transpose().fillna(0).astype(int)

    try:

        to_data_c = to_data.container()
        to_data_c.write(pd.DataFrame(anchor_pos))

        # calculate the positions from distance matrix
        pos = MDS(dissimilarity='precomputed', random_state=0,
                  normalized_stress=False).fit_transform(dists)

        # get convex hull, and calculate the average angle of sides
        angle = statistics.fmean(map(
            lambda p: np.arctan2(pos[p[0], 1] - pos[p[1], 1],
                                 pos[p[0], 0] - pos[p[1], 0]) % (np.pi / 2),
            pairwise(ConvexHull(pos).vertices)))

        # mirroring if set mirror checkbox
        mirror = -1 if st.session_state.get('mirror') else 1

        # rotating with plus angle
        if 'rotate_with' in st.session_state:
            angle += mirror * st.session_state.rotate_with / 180 * np.pi

        # calculcate the rotation + mirror matrix
        rotation_matrix = np.array([[np.cos(angle) * mirror, -np.sin(angle)],
                                   [np.sin(angle) * mirror, np.cos(angle)]])

        # apply the rotation to all position
        pos = (pos @ rotation_matrix)

        # move zero anchor to (0, 0)
        zero_anchor_pos = st.session_state.get('zero_anchor')
        if isinstance(zero_anchor_pos, int):
            pos -= pos[[*distances.keys()].index(zero_anchor_pos)]

        # move all anchor with move_x, move_y
        pos += (st.session_state.get('move_x', 0),
                st.session_state.get('move_y', 0))

        # transpose matrix to reach easily x coords and y coords separatedly
        pos = pos.transpose()

        # calculate min and max points to show a nice scaled view
        minx, maxx = min(pos[0]), max(pos[0])
        miny, maxy = min(pos[1]), max(pos[1])
        if anchor_pos:
            px1, px2, _ = zip(*anchor_pos.values())
            minx, maxx = min(minx, *px1), max(maxx, *px1)
            miny, maxy = min(miny, *px2), max(maxy, *px2)

        rem = min((maxx-minx)*1.1, (maxy-miny)*1.1) / 3

        # start the subplot and scatter all point
        fig, ax = plt.subplots(figsize=((maxx-minx)*1.1 / rem,
                                        (maxy-miny)*1.1 / rem))
        if anchor_pos:
            px1, px2, _ = zip(*anchor_pos.values())
            ax.scatter(px1, px2, c='#000000')
        ax.scatter(*pos)
        to_plot.pyplot(fig)
        plt.close()

        to_data_c.write(pd.DataFrame(pos, columns=[*distances.keys()]))
    except Exception as ex:
        to_table.table(dists)
        to_plot.warning(ex)


def calculate_distances():
    # for each ancor pair we calculate the distance both direction.
    for from_anchor_uid, from_anchor_lid in anchors.items():
        distance_list = distances.setdefault(from_anchor_uid, {})

        for to_anchor_uid, to_anchor_lid in anchors.items():
            if from_anchor_uid == to_anchor_uid:
                distance_list[to_anchor_uid] = 0
                continue

            with st.spinner(f'{from_anchor_uid} to {to_anchor_uid}'):
                dist = measure_distance(from_anchor_uid, to_anchor_lid)
            if dist is not None:
                oth_dist_list = distances.get(to_anchor_uid, {})
                # get the average with the other direction calculated distance
                if from_anchor_uid in oth_dist_list:
                    dist = (oth_dist_list[from_anchor_uid] + dist) // 2
                    oth_dist_list[from_anchor_uid] = dist

                distance_list[to_anchor_uid] = dist

            print_table()


if __name__ == '__main__':
    print_table()
    if st.button('Calculate the distances again'):
        with st.spinner('Calculating the distances...'):
            calculate_distances()

    # the header layout
    lab1, lab2, zero_anchor = to_modifiers.columns([0.1, 0.1, 0.2])
    mir, rot = to_modifiers.columns([0.2, 0.5])
    max_slide = float(pd.DataFrame(distances).abs().max().max())
    lab1.number_input('x', min_value=-max_slide, value=.0, max_value=max_slide,
                      key='move_x', label_visibility='collapsed')
    lab2.number_input('y', min_value=-max_slide, value=.0, max_value=max_slide,
                      key='move_y', label_visibility='collapsed')
    zero_anchor.selectbox('Zero anchor', (None, *anchors), key='zero_anchor',
                          label_visibility='collapsed')
    mir.checkbox('Mirroring', key='mirror')
    rot.slider('Rotate with', max_value=360, key='rotate_with',
               label_visibility='collapsed')
