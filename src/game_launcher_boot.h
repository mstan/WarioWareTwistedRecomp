#pragma once

#include <string>
#include <vector>

#include "runtime.h"

// Returns 1 when the launcher was closed without starting the game, otherwise
// extends args with the committed settings and returns 0.
int game_launcher_preboot(std::vector<std::string>& args,
                          const gbarecomp::RunOptions& opts);
