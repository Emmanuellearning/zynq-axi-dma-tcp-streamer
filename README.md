## Table of Contents
1. [Project Overview](#overview)
2. [Hardware Architecture](#hardware)
3. [FPGA Design — Programmable Logic (PL)](#pl-design)
   - [v1: CORDIC source, 32-bit sampler](#v1)
   - [v2: Counter source, 32-bit (2×16)](#v2)
   - [v3: 64-bit upgrade, 4×16-bit streams](#v3)
4. [Vitis / Software — Processing System (PS)](#ps-design)
   - [Direct streaming (v1)](#direct)
   - [Ping-pong buffers](#pingpong)
   - [Circular buffers](#circular)
5. [Results & Observations](#results)


---

## 1. Project Overview <a name="overview"></a>

The goal of this project is to demonstrate a complete data acquisition pipeline on the Zynq-7020:

- **PL side**: generate or capture a data stream (CORDIC output or counters), apply a custom sampling IP that enforces a 1 µs/sample rate and produces AXI-Stream packets with TLAST asserted every 100 samples.
- **PS side**: receive DMA transfers into DDR memory using the AXI DMA IP connected to the HP0 port, then forward the data to a PC over TCP.
- **PC side**: a GUI application receives the TCP stream and displays it in real time.

in vivado, it is to be noted that we will be using a zynq 7020 board, the board files need to be downloaded and add to the right directory.
<img width="1918" height="1051" alt="image" src="https://github.com/user-attachments/assets/48289b1a-5575-4f50-8ac3-58ac0066ec33" />

---

## 2. Hardware Architecture <a name="hardware"></a>

**Target board**: Zynq-7020 (e.g. Zedboard / PYNQ-Z2 / custom)

### Key IP blocks
| Block | Role |
|---|---|
| Data source (CORDIC / counter) | Produces continuous AXI-Stream data |
| Custom Sampler IP | Rate control, TLAST generation |
| AXI DMA | Moves data from PL stream → PS DDR via HP0 |
| Processing System (PS) | ARM Cortex-A9, runs Vitis bare-metal/FreeRTOS |

Add Processing System

Add a Zynq-7 Processing System to the block diagram and run Block Automation.

Enable High-Performance AXI Interface

Enable the S_AXI_HP0 interface, which is used for high-throughput data transfer between the PL and PS.

<img width="1595" height="962" alt="image" src="https://github.com/user-attachments/assets/506881d1-3b3a-482a-8c5b-d42522d966ef" />
Configure Clock & Ethernet Speed

In the clock configuration settings, ensure the Ethernet speed is set appropriately.

Our pipeline requires only 8–10 Mbps, so setting it to 100 Mbps is sufficient.

<img width="1448" height="951" alt="image" src="https://github.com/user-attachments/assets/68891432-06e6-4b38-9cf0-b5a6b6dfdb8b" />
Interrupts vs Polling

Although interrupts are generally recommended, in this design we will use polling, since no other concurrent tasks are being handled.

<img width="1196" height="909" alt="image" src="https://github.com/user-attachments/assets/79b0fda5-b71a-4f62-84fb-c40ebb72f476" />


AXI DMA Setup
 Add and Configure AXI DMA

Add an AXI DMA block and configure it as shown below:

<img width="1317" height="999" alt="image" src="https://github.com/user-attachments/assets/f61b4267-3ae0-45d1-94b7-56c5ff0b4ace" />

You can select the stream width as required using the configuration menu.

 Run Block Automation

Run Block Automation after adding the AXI DMA. This will automatically connect the necessary interfaces.

You should now see a ready-to-use AXI DMA block with a floating S_AXI_S2MM interface:

<img width="674" height="533" alt="image" src="https://github.com/user-attachments/assets/8eb47c11-5586-485b-8760-a8b0d49708b3" />
Vitis Setup (lwIP Echo Server)
Export Hardware & Create Application

After exporting the .xsa file from Vivado, use it in Vitis to set up a custom echo server application.

 Configure BSP Settings

Before creating the application, go to BSP Settings and ensure that lwIP is selected.

<img width="1910" height="968" alt="image" src="https://github.com/user-attachments/assets/540567d3-501c-43b5-ba42-6581d3e8d48b" />
Match PHY Link Speed

In the lwIP configuration, make sure that:

phy_link_speed matches the Ethernet speed configured in Vivado.

This ensures proper communication between the hardware design and the network stack.

The above settings were followed for every architecture I have done so far. Changes were made in echo.c and main.c to get the desired output.

---

## 3. FPGA Design — Programmable Logic (PL) <a name="pl-design"></a>

### v1: CORDIC source + 32-bit custom sampler <a name="v1"></a>

The first iteration used a **CORDIC IP** configured to output a 32-bit result on an AXI-Stream interface as the data source.

A **custom sampler module** was written in HDL to:
- Accept a 32-bit AXI-Stream input (TDATA, TVALID, TREADY).
- Enforce a 1 µs sample period (clock-divided gate on TREADY/TVALID).
- Count incoming samples and assert **TLAST** after every 100 samples, forming AXI-Stream packets compatible with the AXI DMA S2MM channel.

Block Diagram:
<img width="1006" height="500" alt="image" src="https://github.com/user-attachments/assets/17b66b06-7e03-451c-9978-b23c8dc22055" />

Waveform Recieved on the PC End:
><img width="1600" height="870" alt="image" src="https://github.com/user-attachments/assets/d9a03d97-372b-41c3-a9a7-7dfcc2a96003" />

Some initial issues I faced was while Simple / Linear Streaming, there used to be  breaks every 100 samples, to compact this I set up ping pong buffers. 
Later on i decide to go with Circular buffers. Details about this is mentioned in the vitis section.



The CORDIC block can be replaced with any data stream, allowing you to analyze and study different types of signals effectively.

### v2: 64-bit upgrade — 4×16-bit streams <a name="v3"></a>

The design was extended to capture **four 16-bit AXI-Stream sources** simultaneously, packed into a single **64-bit** wide AXI-Stream. This required:

- Updating the AXI DMA data width to 64 bits (and corresponding changes in Vivado and Vitis driver configuration).
- Writing a new **4-input sampler module** that:
 Synchronizes four independent 16-bit inputs using valid signals, samples them at 1 µs intervals, packs them into a 64-bit AXI-Stream, and transmits in 100-sample frames with proper handshaking.This design ensures that four independent input streams are synchronized, efficiently packed, and reliably transmitted.
By waiting until all inputs are valid at the same time, it guarantees that each 64-bit output word represents data from the same sampling instant, preventing misalignment.
The 1 µs tick enforces a consistent sampling rate, while packing the data into a single wide stream improves DMA efficiency.
Additionally, grouping samples into fixed-size frames using TLAST makes downstream processing and transmission more structured and predictable.

In architecture, I have implemented 4 cordics to generate the required streams.

Block diagram:
<img width="1376" height="538" alt="image" src="https://github.com/user-attachments/assets/18e5772a-7fe4-4ba7-b1ec-f0ba5cbcaac5" />

Output Waveforms:
<img width="1226" height="978" alt="image" src="https://github.com/user-attachments/assets/221e750a-7075-4d67-8218-195fd6763b06" />

Moving further, I wanted to change the characteristics of the my stream using inputs from the pc side with the gui. For this i Setup an axigpio in the PL end.
<img width="1546" height="613" alt="image" src="https://github.com/user-attachments/assets/7628172d-7928-4c85-814f-e9c83b440808" />

By making an input option in the gui:
<img width="1333" height="792" alt="image" src="https://github.com/user-attachments/assets/3e660b51-a4c3-4c92-919a-bc91a2643987" />


---

## 4. Vitis / Software — Processing System (PS) <a name="ps-design"></a>

### v1: Direct streaming (no buffering) <a name="direct"></a>

The first approach submitted a single DMA S2MM transfer for each 100-sample packet. After the transfer completed, the CPU processed the buffer and submitted the next transfer.

**Problem observed**: Visible breaks / gaps in the data stream every 100 samples. The gap occurred during the CPU processing window between one transfer completing and the next being submitted — the DMA was idle during this time, and any incoming stream data was lost or stalled.

<img width="1599" height="1439" alt="image" src="https://github.com/user-attachments/assets/cf1c7482-c817-4fc0-af01-4f44db5412c5" />

### Ping-pong buffers <a name="pingpong"></a>

To eliminate the dead time, a **ping-pong buffer** scheme was implemented:

- Two equally-sized buffers (Buffer A and Buffer B) are allocated in DDR.
- While the DMA writes into Buffer A, the CPU processes Buffer B (and vice versa).
- On each DMA completion interrupt, the roles of the two buffers are swapped, and the DMA is immediately re-armed on the idle buffer.

This effectively hides the CPU processing latency as long as processing one buffer completes before the DMA fills the other. The gaps were eliminated.

<img width="1600" height="822" alt="image" src="https://github.com/user-attachments/assets/dc7eab58-e318-4f4c-b641-4db4a3010321" />


### Circular buffers <a name="circular"></a>

Further improvement was achieved by implementing a **circular (ring) buffer** using the AXI DMA's scatter-gather or cyclic mode:

- A contiguous ring of N buffer descriptors is set up in DDR.
- The DMA automatically advances to the next descriptor on transfer completion, with no CPU intervention required to re-arm.
- The CPU reads completed descriptors from the tail of the ring while the DMA fills new ones at the head.

This proved to be the most efficient approach, offering:
- Lowest CPU overhead (no re-arming needed).
- Maximum sustained throughput.
- No data gaps under normal operation.


## 5. Results & Observations <a name="results"></a>

- The **circular buffer** approach achieved continuous, gap-free streaming at 1 Msps (1 µs/sample).
- The **AND-gated TLAST** in the v3 sampler correctly aligned all four 16-bit streams in the 64-bit output word.
- The **ping-pong buffer** was a useful intermediate step, it worked well with no issues, But i decided to go with Circular buffer as it seemed the best option for future changes.
- Direct streaming (v1) was insufficient for sustained operation at this sample rate.

<img width="1333" height="792" alt="image" src="https://github.com/user-attachments/assets/3e660b51-a4c3-4c92-919a-bc91a2643987" />


I'm still working on improving the current design, this is the first time I'm working with SOC's so some of this might look sloppy, hoping to learn more and
update more. PEACE!
