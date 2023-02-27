 /* -*- P4_16 -*- */
 // win = 64, slide = 30



#include <core.p4>
#if __TARGET_TOFINO__ == 2
#include <t2na.p4>
#else
#include <tna.p4>
#endif
#include "common/headers.p4"
#include "common/util.p4"
/* MACROS */

#if __TARGET_TOFINO__ == 1
typedef bit<3> mirror_type_t;
#else
typedef bit<4> mirror_type_t;
#endif


const bit<16> TYPE_IPV4 = 0x800;
const bit<16> TYPE_8021q = 0x8100;
const bit<8> PROTO_TCP = 6;
const bit<8> PROTO_UDP = 17;
// const bit<9> LOOPBACK_PORT = 68;
const bit<9> LOOPBACK_PORT = 184;
// const bit<9> LOOPBACK_PORT = 28;
const bit<9> FORWARD_PORT = 188;
// cpu port: h3c:192, edgecore:320
const bit<9> CPU_PORT = 192;

// for RE
// const bit<8> MAX_UNIT_NUM = 32;
const bit<8> MAX_UNIT_NUM = 32;
// const bit<8> UNIT_BIT_LEN = 32;
#define UNIT_BIT_LEN 32
const bit<8> UNIT_BYTE_LEN = UNIT_BIT_LEN / 8;
const bit<8> MAX_DEPTH = MAX_UNIT_NUM * UNIT_BIT_LEN / 8; // Byte
// ETH:14B, IP:20B, TCP:20B
const bit<16> ETHER_HEADER_LENGTH = 14;
const bit<16> IPV4_HEADER_LENGTH = 20;
const bit<16> ICMP_HEADER_LENGTH = 8;
const bit<16> TCP_HEADER_LENGTH = 20;
const bit<16> UDP_HEADER_LENGTH = 8;
const bit<8> IP_TCP_LEN = 40;
const bit<8> IP_UDP_LEN = 28;

/*************************************************************************
*********************** H E A D E R S  ***********************************
*************************************************************************/

typedef bit<9>  egressSpec_t;
typedef bit<48> macAddr_t;
typedef bit<32> ip4Addr_t;
typedef bit<9>  port_num_t;
typedef bit<16> num_count_t;
typedef bit<16> upper_count_t;

header ethernet_t {
    macAddr_t dstAddr;
    macAddr_t srcAddr;
    bit<16>   etherType;
}

header ipv4_t {
    bit<4>    version;
    bit<4>    ihl;
    bit<8>    diffserv;
    // bit<16>   totalLen;
    bit<8> totalLen_h;
    bit<8> totalLen_l;
    bit<16>   identification;
    bit<3>    flags;
    bit<13>   fragOffset;
    bit<8>    ttl;
    bit<8>    protocol;
    bit<16>   hdrChecksum;
    ip4Addr_t srcAddr;
    ip4Addr_t dstAddr;
}

header tcp_t {
    bit<16> srcPort;
    bit<16> dstPort;
    bit<32> seqNo;
    bit<32> ackNo;
    bit<4>  dataOffset;
    bit<4>  res;
    bit<8>  flags;
    bit<16> window;
    bit<16> checksum;
    bit<16> urgentPtr;
}

header udp_t {
    bit<16> srcPort;
    bit<16> dstPort;
    bit<16> length_;
    bit<16> checksum;
}


header dns_t {
    bit<16> id;
    bit<1> is_response;
    bit<4> opcode;
    bit<1> auth_answer;
    bit<1> trunc;
    bit<1> recur_desired;
    bit<1> recur_avail;
    bit<1> reserved;
    bit<1> authentic_data;
    bit<1> checking_disabled;
    bit<4> resp_code;
    bit<16> q_count;
    bit<16> answer_count;
    bit<16> auth_rec;
    bit<16> addn_rec;
}



header single_byte_t {
    bit<8> single_byte;
}

header two_bytes_t {
    bit<16> two_bytes;
}

header three_bytes_t {
    bit<24> three_bytes;
}

header payload_unit_t {
    bit<UNIT_BIT_LEN> payload_unit;
}



struct my_ingress_metadata_t {
    bit<4> tcp_dataOffset;
    bit<16> tcp_window;
    bit<16> udp_length;
    bit<16> srcport;
    bit<16> dstport;
    
    bit<32> hashout;
    bit<8> header_len;

    bit<8> hash_sault_1;
    bit<8> hash_sault_2;
    bit<8> hash_sault_3;

    // bit<528> payload;
    // bit<800> payload;
    bit<1024> payload;
    bit<2048> payload_2;

    // SDT result
    bit<4> w_1_SDT_Result_1;
    bit<4> w_1_SDT_Result_2;
    bit<4> w_2_SDT_Result_1;
    bit<4> w_2_SDT_Result_2;
    bit<4> w_3_SDT_Result_1;
    bit<4> w_3_SDT_Result_2;

    // SMF result
    bit<4> w_1_SMF_Result;
    bit<4> w_2_SMF_Result;
    bit<4> w_3_SMF_Result;


}


struct my_ingress_headers_t {
    // my change
    ethernet_t  ethernet;
    ipv4_t      ipv4;
    tcp_t       tcp;
    udp_t       udp;
    payload_unit_t[MAX_UNIT_NUM] payload_units;
    
}

    /***********************  H E A D E R S  ************************/

struct my_egress_headers_t {
}

    /********  G L O B A L   E G R E S S   M E T A D A T A  *********/

struct my_egress_metadata_t {
}



/*************************************************************************
*********************** P A R S E R  ***********************************
*************************************************************************/
parser IngressParser(packet_in        pkt,
    out my_ingress_headers_t          hdr,
    out my_ingress_metadata_t         meta,
    out ingress_intrinsic_metadata_t  ig_intr_md)
{
    ParserCounter() counter_domain;
    
    //TofinoIngressParser() tofino_parser;
    state start {
        pkt.extract(ig_intr_md);
        transition parse_port_metadata;
    }
    
   state parse_port_metadata {
       pkt.advance(PORT_METADATA_SIZE);
       transition init_meta;
   }
   state init_meta {
       transition parse_ethernet;
   }

    state parse_ethernet {
        pkt.extract(hdr.ethernet);
        transition select(hdr.ethernet.etherType) {
            TYPE_IPV4   : parse_ipv4;
            default: accept;
        }
    }
    
   
    state parse_ipv4 {
        // meta.advance_value = 0;
        pkt.extract(hdr.ipv4);
        transition select(hdr.ipv4.ihl) {
            5: dispatch_on_protocol;
            // default: parse_ipv4_options;
        }
        
   }

    state dispatch_on_protocol {
        // counter_domain.set(hdr.ipv4.totalLen);
        counter_domain.set(hdr.ipv4.totalLen_l);
        transition select(hdr.ipv4.protocol) {
            PROTO_TCP   : parse_tcp;
            PROTO_UDP   : parse_udp;
            default: accept;
        }
    }
     
    state parse_tcp {
        pkt.extract(hdr.tcp);
        meta.tcp_dataOffset = hdr.tcp.dataOffset;
        meta.tcp_window = hdr.tcp.window;
        meta.udp_length = 0x0;
        meta.srcport=hdr.tcp.srcPort;
        meta.dstport=hdr.tcp.dstPort;
        // counter_domain.set(hdr.ipv4.totalLen_l, 8w255, 0, 7, -ETH_IP_TCP_LEN);
        counter_domain.decrement(IP_TCP_LEN);
        // meta.header_len = ETH_IP_TCP_LEN;
        transition compare_with_depth;
    }
    
    state parse_udp {
        pkt.extract(hdr.udp);
        meta.tcp_dataOffset = 0x0;
        meta.tcp_window = 0x0;
        meta.udp_length = hdr.udp.length_;
        meta.srcport = hdr.udp.srcPort;
        meta.dstport = hdr.udp.dstPort;
        // counter_domain.set(hdr.ipv4.totalLen_l, 8w255, 0, 7, -ETH_IP_UDP_LEN);
        counter_domain.decrement(IP_UDP_LEN);
        // meta.header_len = ETH_IP_UDP_LEN;
        transition compare_with_depth; 
    }

    state compare_with_depth {
        counter_domain.decrement(MAX_DEPTH);
        transition select(counter_domain.is_negative()) {
            true: L_than_depth;
            false: GE_than_depth;
        }
    }
    

    state L_than_depth {
        counter_domain.increment(MAX_DEPTH);
        transition check_counter_zero;
    }

    // 将长度除以unit_bit_len计算得到可以解析的unit_num
    // state cal_unit_num {
    //     transition select(hdr.ipv4.protocol) {
    //         PROTO_TCP: cal_unit_num_tcp;
    //         PROTO_UDP: cal_unit_num_udp;
    //     } 
    // }

    state GE_than_depth {
        counter_domain.set(MAX_DEPTH);
        // counter_domain.set(MAX_UNIT_NUM);
        transition check_counter_zero;
    }

    state check_counter_zero {
        transition select(counter_domain.is_zero()) {
            true: accept;
            false: parse_payload;
        }
    }

    // @dont_unroll
    state parse_payload {
        pkt.extract(hdr.payload_units.next);
        counter_domain.decrement(UNIT_BYTE_LEN);
        transition select(counter_domain.is_zero()) {
            true: accept;
            false: parse_payload;
        }
    }

}

   
control Ingress(
    /* User */
    inout my_ingress_headers_t                       hdr,
    inout my_ingress_metadata_t                      meta,
    /* Intrinsic */
    in    ingress_intrinsic_metadata_t               ig_intr_md,
    in    ingress_intrinsic_metadata_from_parser_t   ig_prsr_md,
    inout ingress_intrinsic_metadata_for_deparser_t  ig_dprsr_md,
    inout ingress_intrinsic_metadata_for_tm_t        ig_tm_md
     )
{   
    

    action ac_merge_payload() {
        meta.payload[31:0] = hdr.payload_units[0].payload_unit;
        meta.payload[63:32] = hdr.payload_units[1].payload_unit;
        meta.payload[95:64] = hdr.payload_units[2].payload_unit;
        meta.payload[127:96] = hdr.payload_units[3].payload_unit;
        meta.payload[159:128] = hdr.payload_units[4].payload_unit;
        meta.payload[191:160] = hdr.payload_units[5].payload_unit;
        meta.payload[223:192] = hdr.payload_units[6].payload_unit;
        meta.payload[255:224] = hdr.payload_units[7].payload_unit;
        meta.payload[287:256] = hdr.payload_units[8].payload_unit;
        meta.payload[319:288] = hdr.payload_units[9].payload_unit;
        meta.payload[351:320] = hdr.payload_units[10].payload_unit;
        meta.payload[383:352] = hdr.payload_units[11].payload_unit;
        meta.payload[415:384] = hdr.payload_units[12].payload_unit;
        meta.payload[447:416] = hdr.payload_units[13].payload_unit;
        meta.payload[479:448] = hdr.payload_units[14].payload_unit;
        meta.payload[511:480] = hdr.payload_units[15].payload_unit;
        
        meta.payload[543:512] = hdr.payload_units[16].payload_unit;
        meta.payload[575:544] = hdr.payload_units[17].payload_unit;
        meta.payload[607:576] = hdr.payload_units[18].payload_unit;
        meta.payload[639:608] = hdr.payload_units[19].payload_unit;
        meta.payload[671:640] = hdr.payload_units[20].payload_unit;
        meta.payload[703:672] = hdr.payload_units[21].payload_unit;
        meta.payload[735:704] = hdr.payload_units[22].payload_unit;
        meta.payload[767:736] = hdr.payload_units[23].payload_unit;
        meta.payload[799:768] = hdr.payload_units[24].payload_unit;
        meta.payload[831:800] = hdr.payload_units[25].payload_unit;
        meta.payload[863:832] = hdr.payload_units[26].payload_unit;
        meta.payload[895:864] = hdr.payload_units[27].payload_unit;
        meta.payload[927:896] = hdr.payload_units[28].payload_unit;
        meta.payload[959:928] = hdr.payload_units[29].payload_unit;
        meta.payload[991:960] = hdr.payload_units[30].payload_unit;
        meta.payload[1023:992] = hdr.payload_units[31].payload_unit;
    }

    @pragma stage 0
    table tb_merge_payload {
        actions = {
            ac_merge_payload;
        }
        default_action = ac_merge_payload;
        size = 1;
    }

    // window 1
    // table for SDT

    action ac_w_1_SDT_1(bit<4> sdt_result) {
        meta.w_1_SDT_Result_1 = sdt_result;
    }

    @pragma stage 1
    table tb_w_1_SDT_1 {
        key = {
            meta.payload[511:0]: ternary;
        }
        actions = {
            ac_w_1_SDT_1;
        }
        size = 256;
    }

    action ac_w_1_SDT_2(bit<4> sdt_result) {
        meta.w_1_SDT_Result_2 = sdt_result;
    }

    @pragma stage 1
    table tb_w_1_SDT_2 {
        key = {
            meta.payload[511:0]: ternary;
        }
        actions = {
            ac_w_1_SDT_2;
        }
        size = 256;
    }


    // table for SDT voting
    action ac_w_1_SDT_vote(bit<4> vote_result) {
        meta.w_1_SMF_Result = vote_result;
    }

    @pragma stage 2
    table tb_w_1_SDT_vote {
        key = {
            meta.w_1_SDT_Result_1: exact;
            meta.w_1_SDT_Result_2: exact;
        }
        actions = {
            ac_w_1_SDT_vote;
        }
        size = 16;
    }

    // window 2
    action ac_w_2_SDT_1(bit<4> sdt_result) {
        meta.w_2_SDT_Result_1 = sdt_result;
    }

    @pragma stage 1
    table tb_w_2_SDT_1 {
        key = {
            meta.payload[751:239]: ternary;
        }
        actions = {
            ac_w_2_SDT_1;
        }
        size = 256;
    }

    action ac_w_2_SDT_2(bit<4> sdt_result) {
        meta.w_2_SDT_Result_2 = sdt_result;
    }

    @pragma stage 1
    table tb_w_2_SDT_2 {
        key = {
            meta.payload[751:239]: ternary;
        }
        actions = {
            ac_w_2_SDT_2;
        }
        size = 256;
    }


    // table for SDT voting
    action ac_w_2_SDT_vote(bit<4> vote_result) {
        meta.w_2_SMF_Result = vote_result;
    }

    @pragma stage 2
    table tb_w_2_SDT_vote {
        key = {
            meta.w_2_SDT_Result_1: exact;
            meta.w_2_SDT_Result_2: exact;
        }
        actions = {
            ac_w_2_SDT_vote;
        }
        size = 16;
    }

    // window 3
    action ac_w_3_SDT_1(bit<4> sdt_result) {
        meta.w_3_SDT_Result_1 = sdt_result;
    }

    // @pragma stage 1
    table tb_w_3_SDT_1 {
        key = {
            meta.payload[959:479]: ternary;
        }
        actions = {
            ac_w_3_SDT_1;
        }
        size = 256;
    }

    action ac_w_3_SDT_2(bit<4> sdt_result) {
        meta.w_3_SDT_Result_2 = sdt_result;
    }

    // @pragma stage 1
    table tb_w_3_SDT_2 {
        key = {
            meta.payload[959:479]: ternary;
        }
        actions = {
            ac_w_3_SDT_2;
        }
        size = 256;
    }


    // table for SDT voting
    action ac_w_3_SDT_vote(bit<4> vote_result) {
        meta.w_3_SMF_Result = vote_result;
    }

    // @pragma stage 2
    table tb_w_3_SDT_vote {
        key = {
            meta.w_3_SDT_Result_1: exact;
            meta.w_3_SDT_Result_2: exact;
        }
        actions = {
            ac_w_3_SDT_vote;
        }
        size = 16;
    }

    // decision table, use egress port as an example
    action ac_decision(bit<9> eg_port) {
        ig_tm_md.ucast_egress_port = eg_port;
    }

    @pragma stage 3
    table tb_decision {
        key = {
            meta.w_1_SMF_Result: exact;
            meta.w_2_SMF_Result: exact;
            meta.w_3_SMF_Result: exact;
        }
        actions = {
            ac_decision;
        }
        size = 8;
    }

    apply {
        tb_merge_payload.apply();
        tb_w_1_SDT_1.apply();
        tb_w_1_SDT_2.apply();
        tb_w_1_SDT_vote.apply();
        tb_w_2_SDT_1.apply();
        tb_w_2_SDT_2.apply();
        tb_w_2_SDT_vote.apply();
        tb_w_3_SDT_1.apply();
        tb_w_3_SDT_2.apply();
        tb_w_3_SDT_vote.apply();
        tb_decision.apply();
        // ig_tm_md.ucast_egress_port = FORWARD_PORT;

        ig_tm_md.bypass_egress = 1w1;
    }
  
}


control IngressDeparser(packet_out pkt,
    /* User */
    inout my_ingress_headers_t                       hdr,
    in    my_ingress_metadata_t                      meta,
    /* Intrinsic */
    in    ingress_intrinsic_metadata_for_deparser_t  ig_dprsr_md)
{
   // Resubmit() resubmit;
    apply {
        // resubmit with resubmit_data
      // if (ig_dprsr_md.resubmit_type == 2) {
      //     resubmit.emit(meta.resubmit_data);
      // }
        pkt.emit(hdr);
    }
}



/*************************************************************************
***********************  S W I T C H  *******************************
*************************************************************************/

/************ F I N A L   P A C K A G E ******************************/
Pipeline(
    IngressParser(),
    Ingress(),
    IngressDeparser(),
    EmptyEgressParser(),
    EmptyEgress(),
    EmptyEgressDeparser()
) pipe;

Switch(pipe) main;


