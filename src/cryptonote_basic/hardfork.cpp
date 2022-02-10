// Copyright (c) 2014-2018, The Monero Project
// Copyright (c)      2018, The Beldex Project
// 
// All rights reserved.
// 
// Redistribution and use in source and binary forms, with or without modification, are
// permitted provided that the following conditions are met:
// 
// 1. Redistributions of source code must retain the above copyright notice, this list of
//    conditions and the following disclaimer.
// 
// 2. Redistributions in binary form must reproduce the above copyright notice, this list
//    of conditions and the following disclaimer in the documentation and/or other
//    materials provided with the distribution.
// 
// 3. Neither the name of the copyright holder nor the names of its contributors may be
//    used to endorse or promote products derived from this software without specific
//    prior written permission.
// 
// THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY
// EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
// MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL
// THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
// SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
// PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
// INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
// STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF
// THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

#include <array>

#include "hardfork.h"
#include "epee/syncobj.h"

namespace cryptonote {

// version 7 from the start of the blockchain, inhereted from Monero mainnet
static constexpr std::array mainnet_hard_forks =
{
  hard_fork{1,  0,       1,  1548750273 }, // Beldex 0.1: Beldex is born
  hard_fork{7,  0,      10,  1548750283 },
  hard_fork{8,  0,    40000, 1559474448 },
  hard_fork{11, 0,    56240, 1577836800 },
  hard_fork{12, 0,   126874, 1578704502 },
  hard_fork{15, 0,   742420, 1636320320 }, //Friday, December 10, 2021 6:00:00 PM (GMT)
  hard_fork{17, 0,   742421, 1636320540 },
};

static constexpr std::array testnet_hard_forks =
{
  hard_fork{1,  0,        1, 1548474440 },
  hard_fork{7,  0,       10, 1559474448 },
  hard_fork{8,  0,    40000, 1559474448 },
  hard_fork{11, 0,    54288, 1628224369 },
  hard_fork{12, 0,   104832, 1629012232 }, // Sunday, August 15, 2021 7:23:52 AM
  hard_fork{15, 0,   169950, 1636391396 }, //  Monday, November 8, 2021 5:09:56 PM
  hard_fork{17, 0,   169960, 1636391696 }, // Monday, November 8, 2021 5:14:56 PM
};

static constexpr std::array devnet_hard_forks =
{
  hard_fork{ 7, 0,      0,  1599848400 },
  hard_fork{ 17, 0,     2,  1599848400 },
};

template <size_t N>
static constexpr bool is_ordered(const std::array<hard_fork, N>& forks) {
  if (N == 0 || forks[0].version < 1)
    return false;
  for (size_t i = 1; i < N; i++) {
    auto& hf = forks[i];
    auto& prev = forks[i-1];
    if ( // [major,mnoderevision] pair must be strictly increasing (lexicographically)
        std::make_pair(hf.version, hf.mnode_revision) <= std::make_pair(prev.version, prev.mnode_revision)
        // height must be strictly increasing; time must be weakly increasing
        || hf.height <= prev.height || hf.time < prev.time)
      return false;
  }
  return true;
}

static_assert(is_ordered(mainnet_hard_forks),
    "Invalid mainnet hard forks: version must start at 1, major versions and heights must be strictly increasing, and timestamps must be non-decreasing");
static_assert(is_ordered(testnet_hard_forks),
    "Invalid testnet hard forks: version must start at 1, versions and heights must be strictly increasing, and timestamps must be non-decreasing");
static_assert(is_ordered(devnet_hard_forks),
    "Invalid devnet hard forks: version must start at 1, versions and heights must be strictly increasing, and timestamps must be non-decreasing");

std::vector<hard_fork> fakechain_hardforks;

std::pair<const hard_fork*, const hard_fork*> get_hard_forks(network_type type)
{
  if (type == network_type::MAINNET) return {&mainnet_hard_forks[0], &mainnet_hard_forks[mainnet_hard_forks.size()]};
  if (type == network_type::TESTNET) return {&testnet_hard_forks[0], &testnet_hard_forks[testnet_hard_forks.size()]};
  if (type == network_type::DEVNET) return {&devnet_hard_forks[0], &devnet_hard_forks[devnet_hard_forks.size()]};
  if (type == network_type::FAKECHAIN) return {fakechain_hardforks.data(), fakechain_hardforks.data() + fakechain_hardforks.size()};
  return {nullptr, nullptr};
}


std::pair<std::optional<uint64_t>, std::optional<uint64_t>>
get_hard_fork_heights(network_type nettype, uint8_t version) {
  std::pair<std::optional<uint64_t>, std::optional<uint64_t>> found;
  for (auto [it, end] = get_hard_forks(nettype); it != end; it++) {
    if (it->version > version) { // This (and anything else) are in the future
      if (found.first) // Found something suitable in the previous iteration, so one before this hf is the max
        found.second = it->height - 1;
      break;
    } else if (it->version == version && !found.first) {
      found.first = it->height;
    }
  }
  return found;
}

cryptonote::hard_fork index;
// uint8_t get_current_version();
uint8_t get_current_version()
{
  CRITICAL_REGION_LOCAL(lock);
  return height[index.current_fork_index].version;
}

uint8_t hard_fork_ceil(network_type nettype, uint8_t version) {
  auto [it, end] = get_hard_forks(nettype);
  for (; it != end; it++)
    if (it->version >= version)
      return it->version;

  return version;
}

std::pair<uint8_t, uint8_t>
get_network_version_revision(network_type nettype, uint64_t height) {
  std::pair<uint8_t, uint8_t> result;
  for (auto [it, end] = get_hard_forks(nettype); it != end; it++) {
    if (it->height <= height)
      result = {it->version, it->mnode_revision};
    else
      break;
  }
  return result;
}

bool is_hard_fork_at_least(network_type type, uint8_t version, uint64_t height) {
  return get_network_version(type, height) >= version;
}

std::pair<uint8_t, uint8_t>
get_ideal_block_version(network_type nettype, uint64_t height)
{
  std::pair<uint8_t, uint8_t> result;
  for (auto [it, end] = get_hard_forks(nettype); it != end; it++) {
    if (it->height <= height)
      result.first = it->version;
    result.second = it->version;
  }
  return result;
}
}