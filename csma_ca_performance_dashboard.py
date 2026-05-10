import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt


class Buffer:
    def __init__(self):
        self.frames = [1]

    def get_frame(self):
        if self.frames:
            return self.frames.pop(0)
        return None

    def add_frame(self):
        self.frames.append(1)


class WLANNode:
    def __init__(self, node_id, transmission_slots, cw_min, cw_max, is_hidden=False):
        self.node_id = node_id
        self.is_hidden = is_hidden

        self.CW_min = cw_min
        self.CW_max = cw_max
        self.CW_current = self.CW_min

        self.backoff_time = 0
        self.decrement_difs_count = 0
        self.deffer = 5
        self.state = "DIFS"

        self.txop = 0
        self.successful_transmission = 0
        self.collision = 0
        self.retry = 0
        self.frame_dropped = 0

        self.buffer = Buffer()

        self.slot_counter = 0
        self.channel_state = "Idle"
        self.prev_channel_state = "Idle"

        self.transmission_slots = transmission_slots
        self.original_transmission_slots = transmission_slots

        self.CST = -82
        self.transmission_power = 20

        self.sensing_nodes = []
        self.collision_occurred = False

        self.deffer_slots = 0
        self.backoff_slots = 0
        self.transmission_count = 0

        all_cw_values = [31, 63, 127, 255, 511, 1023]

        self.CW_frequencies = {
            cw: 0 for cw in all_cw_values if cw <= self.CW_max
        }

    def set_state(self, state):
        self.state = state

    def decrement_difs(self):
        if self.deffer > 0:
            self.deffer -= 1
            self.deffer_slots += 1

            if self.deffer == 0:
                self.decrement_difs_count += 1
                self.set_state("Perform carrier sense")
                self.generate_backoff()

    def generate_backoff(self):
        if (
            self.state == "Perform carrier sense"
            and self.channel_state == "Idle"
            and self.backoff_time == 0
        ):
            self.backoff_time = np.random.randint(self.CW_min, self.CW_current + 1)
            self.set_state("Backoff")

            if self.backoff_time == 0:
                self.txop += 1

                if self.CW_current in self.CW_frequencies:
                    self.CW_frequencies[self.CW_current] += 1

                self.state = "Transmit"
        else:
            self.state = "Backoff"

    def decrement_backoff(self):
        if self.channel_state == "Idle" and self.state == "Backoff":
            self.slot_counter += 1

            if self.slot_counter == 1:
                self.backoff_slots += 1

            if self.slot_counter == 2:
                if self.backoff_time > 0:
                    self.backoff_time -= 1

                self.slot_counter = 0
                self.backoff_slots += 1

            if self.backoff_time == 0:
                self.txop += 1

                if self.CW_current in self.CW_frequencies:
                    self.CW_frequencies[self.CW_current] += 1

                self.state = "Transmit"

    def drop_frame_and_reset(self):
        self.buffer.get_frame()
        self.buffer.add_frame()
        self.CW_current = self.CW_min
        self.retry = 0

    def transmitting_frame(self, nodes, shared_channel_status):
        transmitting_nodes = [node for node in nodes if node.state == "Transmit"]

        if shared_channel_status == "Busy":
            self.slot_counter += 1

            if self.slot_counter == 2:
                if self.transmission_slots > 0:
                    self.transmission_slots -= 1
                    self.transmission_count += 1

                self.slot_counter = 0

                if len(transmitting_nodes) > 1:
                    self.collision_occurred = True

            if self.transmission_slots == 0:
                if self.collision_occurred:
                    self.collision += 1
                    self.collision_occurred = False
                    self.retry += 1

                    self.CW_current = (2 * self.CW_current) + 1

                    if self.CW_current > self.CW_max:
                        self.CW_current = self.CW_max

                    if self.retry >= 6:
                        self.frame_dropped += 1
                        self.drop_frame_and_reset()
                else:
                    self.successful_transmission += 1
                    self.buffer.get_frame()
                    self.buffer.add_frame()
                    self.CW_current = self.CW_min
                    self.retry = 0

                self.set_state("DIFS")
                self.deffer = 5
                self.transmission_slots = self.original_transmission_slots

    def update_channel_state(self, channel_energy):
        if self.state == "Transmit":
            self.channel_state = "MAC Off"
            self.prev_channel_state = self.channel_state
            return

        if self.is_hidden:
            self.channel_state = "Idle"
            self.prev_channel_state = self.channel_state
            return

        sensed_transmitting_nodes = [
            node for node in self.sensing_nodes
            if node.state == "Transmit"
        ]

        if sensed_transmitting_nodes and self.CST < channel_energy:
            self.channel_state = "Busy"
        else:
            self.channel_state = "Idle"

        if self.prev_channel_state in ["Busy", "MAC Off"] and self.channel_state == "Idle":
            self.set_state("DIFS")
            self.deffer = 5

        self.prev_channel_state = self.channel_state

    def set_sensing_nodes(self, nodes):
        self.sensing_nodes = nodes

    def calculate_average_cwmin_txop(self):
        weighted_cw = sum(cw * freq for cw, freq in self.CW_frequencies.items())

        if self.txop > 0:
            return round((weighted_cw / self.txop) / 2, 2)

        return 0

    def calculate_average_cwmin_successful(self):
        weighted_cw = sum(cw * freq for cw, freq in self.CW_frequencies.items())

        if self.successful_transmission > 0:
            return round((weighted_cw / self.successful_transmission) / 2, 2)

        return 0

    def calculate_average_defer_per_txop(self):
        if self.txop > 0:
            return round(self.decrement_difs_count / self.txop, 2)

        return 0

    def calculate_statistics(self):
        average_cwmin_txop = self.calculate_average_cwmin_txop()
        average_cwmin_successful = self.calculate_average_cwmin_successful()
        average_defer_per_txop = self.calculate_average_defer_per_txop()

        average_defer_time_per_txop = average_defer_per_txop * 50
        average_backoff_time_per_txop = average_cwmin_txop * 20
        average_access_time_per_txop = average_defer_time_per_txop + average_backoff_time_per_txop

        stats = {
            "Node ID": self.node_id,
            "Node Type": "Hidden Node" if self.is_hidden else "Normal Node",
            "CW Min": self.CW_min,
            "CW Max": self.CW_max,
            "Total TXOP": self.txop,
            "Successful Transmission": self.successful_transmission,
            "Collision": self.collision,
            "Frame Dropped": self.frame_dropped,
            "Average FER (%)": round((self.collision / self.txop) * 100, 2) if self.txop > 0 else 0,
            "Average Defer per TXOP": average_defer_per_txop,
            "Average CWmin per TXOP": average_cwmin_txop,
            "Average CWmin per Successful TX": average_cwmin_successful,
            "Average Defer Time per TXOP (µs)": average_defer_time_per_txop,
            "Average Backoff Time per TXOP (µs)": average_backoff_time_per_txop,
            "Average Access Time per TXOP (µs)": average_access_time_per_txop,
            "Transmission Power": self.transmission_power,
        }

        for cw, freq in self.CW_frequencies.items():
            stats[f"CW {cw} Frequency"] = freq

        return stats


def run_simulation(num_nodes, hidden_nodes_count, tx_slots, time_slots, cw_min, cw_max):
    idle_slots = 0
    busy_slots = 0
    channel_energy = -100
    shared_channel_status = "Idle"

    node_ids = [f"AP{i}" for i in range(1, num_nodes + 1)]
    nodes = []

    for i, node_id in enumerate(node_ids):
        is_hidden = i < hidden_nodes_count
        nodes.append(WLANNode(node_id, tx_slots, cw_min, cw_max, is_hidden=is_hidden))

    sensing_matrix = np.ones((num_nodes, num_nodes), dtype=int)
    np.fill_diagonal(sensing_matrix, 0)

    for i in range(num_nodes):
        sensing_nodes_for_i = []

        for j in range(num_nodes):
            if sensing_matrix[i][j] == 1:
                sensing_nodes_for_i.append(nodes[j])

        nodes[i].set_sensing_nodes(sensing_nodes_for_i)

    progress_bar = st.progress(0)

    for slot in range(1, time_slots + 1):
        if any(node.state == "Transmit" for node in nodes):
            channel_energy = -40
            shared_channel_status = "Busy"
            busy_slots += 1
        else:
            channel_energy = -100
            shared_channel_status = "Idle"
            idle_slots += 1

        for node in nodes:
            node.update_channel_state(channel_energy)

        for node in nodes:
            if node.state == "DIFS":
                node.decrement_difs()
            elif node.state == "Perform carrier sense":
                node.generate_backoff()
            elif node.state == "Backoff":
                node.decrement_backoff()
            elif node.state == "Transmit":
                node.transmitting_frame(nodes, shared_channel_status)

        if slot % max(1, time_slots // 100) == 0:
            progress_bar.progress(slot / time_slots)

    node_statistics = [node.calculate_statistics() for node in nodes]
    df_statistics = pd.DataFrame(node_statistics)

    network_average = df_statistics.mean(numeric_only=True).to_frame().T
    network_average.insert(0, "Metric Type", "Average Network Performance")

    return df_statistics, network_average


st.set_page_config(
    page_title="CSMA/CA WLAN Hidden Node Dashboard",
    page_icon="",
    layout="wide"
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    div[data-testid="stMetric"] {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        padding: 18px;
        border-radius: 16px;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.07);
    }

    .main-title {
        text-align: center;
        font-size: 44px;
        font-weight: 800;
        color: #0f172a;
    }

    .subtitle {
        text-align: center;
        font-size: 18px;
        color: #64748b;
        margin-bottom: 30px;
    }

    .info-box {
        background-color: #eff6ff;
        border-left: 6px solid #2563eb;
        padding: 16px;
        border-radius: 12px;
        margin-bottom: 25px;
        color: #1e293b;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="main-title"> CSMA/CA WLAN Simulator</div>
    <div class="subtitle">
        Interactive dashboard for analyzing MAC mechansim.
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="info-box">
    <b>Hidden node model:</b> Hidden nodes do not defer their transmission when the channel is busy.
    In this simulator, hidden nodes always sense the channel as idle and may transmit while other nodes are already transmitting.
    </div>
    """,
    unsafe_allow_html=True
)

st.sidebar.header(" Simulation Inputs")

num_nodes = st.sidebar.number_input(
    "Number of WLAN Nodes",
    min_value=1,
    max_value=100,
    value=1,
    step=1
)

hidden_nodes_count = st.sidebar.number_input(
    "Number of Hidden Nodes",
    min_value=0,
    max_value=num_nodes - 1,
    value=0,
    step=1
)

cw_min = st.sidebar.number_input(
    "Minimum CW Value",
    min_value=31,
    max_value=31,
    value=31,
    step=1,
    disabled=True
)

cw_max = st.sidebar.selectbox(
    "Maximum CW Value",
    options=[63, 127, 255, 511, 1023],
    index=4
)

tx_slots = st.sidebar.number_input(
    "Frame Transmission Slots",
    min_value=1,
    max_value=200,
    value=20,
    step=1
)

time_slots = st.sidebar.number_input(
    "Total Simulation Time Slots",
    min_value=10000,
    max_value=1000000000,
    value=100000,
    step=1000
)

run_button = st.sidebar.button(" Run Simulation", use_container_width=True)


if run_button:
    with st.spinner("Running CSMA/CA hidden-node simulation..."):
        df_statistics, network_average = run_simulation(
            num_nodes,
            hidden_nodes_count,
            tx_slots,
            time_slots,
            cw_min,
            cw_max
        )

    st.success("Simulation completed successfully.")

    avg = network_average.iloc[0]

    st.markdown("## Network Average Performance")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Average TXOP", round(avg["Total TXOP"], 2))
    col2.metric("Average Successful TX", round(avg["Successful Transmission"], 2))
    col3.metric("Average FER (%)", round(avg["Average FER (%)"], 2))
    col4.metric(
        "Average Access Time per TXOP (µs)",
        round(avg["Average Access Time per TXOP (µs)"], 2)
    )

    col5, col6, col7, col8 = st.columns(4)

    col5.metric("CW Min", int(avg["CW Min"]))
    col6.metric("CW Max", int(avg["CW Max"]))
    col7.metric(
        "Average Defer Time per TXOP (µs)",
        round(avg["Average Defer Time per TXOP (µs)"], 2)
    )
    col8.metric(
        "Average Backoff Time per TXOP (µs)",
        round(avg["Average Backoff Time per TXOP (µs)"], 2)
    )

    display_columns = [
        "Node ID",
        "Node Type",
        "CW Min",
        "CW Max",
        "Total TXOP",
        "Successful Transmission",
        "Average FER (%)",
        "Average Access Time per TXOP (µs)",
        "Average CWmin per TXOP",
        "Average Defer Time per TXOP (µs)",
        "Average Backoff Time per TXOP (µs)",
        "Frame Dropped",
    ]

    st.markdown("##  Hidden Node Performance")

    hidden_df = df_statistics[df_statistics["Node Type"] == "Hidden Node"]

    if hidden_df.empty:
        st.info("No hidden nodes were selected for this simulation.")
    else:
        hidden_avg = hidden_df.mean(numeric_only=True)

        h1, h2, h3, h4 = st.columns(4)

        h1.metric("Hidden Avg TXOP", round(hidden_avg["Total TXOP"], 2))
        h2.metric("Hidden Avg Successful TX", round(hidden_avg["Successful Transmission"], 2))
        h3.metric("Hidden Avg FER (%)", round(hidden_avg["Average FER (%)"], 2))
        h4.metric(
            "Hidden Avg Access Time per TXOP (µs)",
            round(hidden_avg["Average Access Time per TXOP (µs)"], 2)
        )

        st.dataframe(
            hidden_df[display_columns],
            use_container_width=True,
            hide_index=True
        )

    st.markdown("##  Normal Node Performance")

    normal_df = df_statistics[df_statistics["Node Type"] == "Normal Node"]

    if normal_df.empty:
        st.info("No normal nodes were selected for this simulation.")
    else:
        normal_avg = normal_df.mean(numeric_only=True)

        n1, n2, n3, n4 = st.columns(4)

        n1.metric("Normal Avg TXOP", round(normal_avg["Total TXOP"], 2))
        n2.metric("Normal Avg Successful TX", round(normal_avg["Successful Transmission"], 2))
        n3.metric("Normal Avg FER (%)", round(normal_avg["Average FER (%)"], 2))
        n4.metric(
            "Normal Avg Access Time per TXOP (µs)",
            round(normal_avg["Average Access Time per TXOP (µs)"], 2)
        )

        st.dataframe(
            normal_df[display_columns],
            use_container_width=True,
            hide_index=True
        )

    st.markdown("## All Performance Graphs")

    graph_metrics = [
        "Successful Transmission",
        "Total TXOP",
        "Average FER (%)",
        "Average Access Time per TXOP (µs)",
        "Average CWmin per TXOP",
        "Average Defer Time per TXOP (µs)",
        "Average Backoff Time per TXOP (µs)",
        "Frame Dropped",
    ]

    for metric in graph_metrics:
        fig, ax = plt.subplots(figsize=(12, 4))

        colors = [
            "#dc2626" if node_type == "Hidden Node" else "#2563eb"
            for node_type in df_statistics["Node Type"]
        ]

        ax.bar(df_statistics["Node ID"], df_statistics[metric], color=colors)
        ax.set_xlabel("WLAN Nodes")
        ax.set_ylabel(metric)
        ax.set_title(f"{metric} per Node")
        ax.tick_params(axis="x", rotation=45)
        ax.grid(axis="y", linestyle="--", alpha=0.4)

        st.pyplot(fig)

    st.markdown("## CW Frequency Distribution for All Nodes")

    all_cw_columns = [
        "CW 31 Frequency",
        "CW 63 Frequency",
        "CW 127 Frequency",
        "CW 255 Frequency",
        "CW 511 Frequency",
        "CW 1023 Frequency"
    ]

    cw_columns = [
        col for col in all_cw_columns
        if col in df_statistics.columns
    ]

    cw_data = df_statistics[["Node ID"] + cw_columns].set_index("Node ID")

    st.dataframe(cw_data, use_container_width=True)

    st.bar_chart(cw_data)

    st.markdown("## Full Per-Node Performance Table")

    st.dataframe(
        df_statistics[display_columns],
        use_container_width=True,
        hide_index=True
    )

    with st.expander("View full raw statistics"):
        st.dataframe(df_statistics, use_container_width=True, hide_index=True)

    csv_data = df_statistics.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="⬇️ Download Results as CSV",
        data=csv_data,
        file_name=f"csma_ca_hidden_node_results_{num_nodes}_nodes.csv",
        mime="text/csv",
        use_container_width=True
    )

else:
    st.info("Enter simulation parameters in the sidebar and click **Run Simulation**.")
