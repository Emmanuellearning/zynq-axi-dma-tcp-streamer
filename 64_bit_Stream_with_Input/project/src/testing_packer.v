module axis_stream_packer_new (

    input  wire aclk,
    input  wire aresetn,

    // 4 independent 16-bit inputs
    input  wire [15:0] in0,
    input  wire [15:0] in1,
    input  wire [15:0] in2,
    input  wire [15:0] in3,

    input  wire        in_valid0,
    input  wire        in_valid1,
    input  wire        in_valid2,
    input  wire        in_valid3,

    // AXIS output
    output reg  [63:0] m_axis_tdata,
    output reg         m_axis_tvalid,
    output reg         m_axis_tlast,
    input  wire        m_axis_tready

);

// -----------------------------
// 1 µs tick generator
// -----------------------------
reg [5:0] us_div = 0;
reg sample_tick = 0;

always @(posedge aclk)
begin
    if (!aresetn)
    begin
        us_div <= 0;
        sample_tick <= 0;
    end
    else
    begin
        if (us_div == 49)
        begin
            us_div <= 0;
            sample_tick <= 1;
        end
        else
        begin
            us_div <= us_div + 1;
            sample_tick <= 0;
        end
    end
end

// -----------------------------
// AXI streaming logic
// -----------------------------
reg [6:0] sample_count = 0;

// all inputs valid together
wire all_valid = in_valid0 & in_valid1 & in_valid2 & in_valid3;

always @(posedge aclk)
begin
    if (!aresetn)
    begin
        m_axis_tvalid <= 0;
        m_axis_tlast  <= 0;
        sample_count  <= 0;
    end

    else
    begin

        // hold until accepted
        if (m_axis_tvalid && !m_axis_tready)
        begin
            m_axis_tvalid <= 1;
        end

        // sample only when tick AND all inputs valid
        else if (sample_tick && all_valid)
        begin
            m_axis_tdata <= {in3, in2, in1, in0};
            m_axis_tvalid <= 1;

            if (sample_count == 99)
            begin
                m_axis_tlast <= 1;
                sample_count <= 0;
            end
            else
            begin
                m_axis_tlast <= 0;
                sample_count <= sample_count + 1;
            end
        end

        else
        begin
            m_axis_tvalid <= 0;
            m_axis_tlast  <= 0;
        end

    end
end

endmodule