# Copyright (c) 2018, The Beldex Project
# Copyright (c) 2014-2018, The Monero Project
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification, are
# permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this list of
#    conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice, this list
#    of conditions and the following disclaimer in the documentation and/or other
#    materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors may be
#    used to endorse or promote products derived from this software without specific
#    prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL
# THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF
# THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

add_library(rpc_commands
  core_rpc_server_commands_defs.cpp
  )

add_library(rpc_server_base
  rpc_args.cpp
  http_server_base.cpp
  )

add_library(rpc
  bootstrap_daemon.cpp
  core_rpc_server.cpp
  )
 
set(daemon_rpc_server_sources
  daemon_handler.cpp
  zmq_server.cpp)

set(daemon_rpc_server_private_headers
  message.h
  daemon_messages.h
  daemon_handler.h
  zmq_server.h)

add_library(daemon_rpc_server
  ${daemon_rpc_server_sources}
  ${daemon_rpc_server_private_headers}
  http_server.cpp
  lmq_server.cpp
  )


add_library(rpc_http_client
    http_client.cpp
    )

add_library(daemon_messages
  message.cpp
  daemon_messages.cpp
  message.h
  daemon_messages.h
  )
  

target_link_libraries(daemon_messages
  PUBLIC
    epee
    cryptonote_core
    cryptonote_protocol
    version
    serialization
    extra
    )

target_link_libraries(rpc_commands
  PUBLIC
    common
    cpr::cpr
    cryptonote_protocol
    extra)

target_link_libraries(rpc_server_base
  PUBLIC
    common
    uWebSockets
    extra)

target_link_libraries(rpc
  PUBLIC
    cryptonote_core
    rpc_commands
    rpc_server_base
    net
    version
    cryptonote_protocol
    Boost::thread
    ${Boost_REGEX_LIBRARY}
    ${Boost_THREAD_LIBRARY}
    Boost::program_options
    OpenSSL::SSL
    extra)

target_link_libraries(daemon_rpc_server
  PUBLIC
    cryptonote_core
    rpc_server_base
    rpc
    Boost::thread
    ${Boost_CHRONO_LIBRARY}
    ${Boost_REGEX_LIBRARY}
    ${Boost_SYSTEM_LIBRARY}
    ${Boost_THREAD_LIBRARY}
    ${ZMQ_LIB}
    ${EXTRA_LIBRARIES}
    extra)

target_link_libraries(rpc_http_client
  PUBLIC
    common
    cpr::cpr
    extra)
    # target_include_directories(daemon_rpc_server PUBLIC ${ZMQ_INCLUDE_PATH})
    # target_include_directories(obj_daemon_rpc_server PUBLIC ${ZMQ_INCLUDE_PATH})
    