import time
from pycaw.pycaw import AudioUtilities

# ────────────────────────────────────────────────
# SETTINGS
# ────────────────────────────────────────────────

SLOW_INTERVAL   = 4.0       # seconds - calm mode
FAST_INTERVAL   = 0.5       # seconds - when we think user is adjusting
FAST_DURATION   = 10.0      # stay fast for this long after detection

TOLERANCE_DB    = 0.4       # only balance if difference bigger than this
DELTA_THRESHOLD = 1.2       # dB - how much bigger one delta needs to be to consider it "the adjusted channel"

# ────────────────────────────────────────────────

def get_volume():
    speakers = AudioUtilities.GetSpeakers()
    return speakers.EndpointVolume


def adaptive_smart_balance():
    print("Starting **smart adaptive** balance monitor...")
    print("Tries to detect which channel is being adjusted and syncs the other one")
    print(f"Slow: {SLOW_INTERVAL}s  |  Fast: {FAST_INTERVAL}s for {FAST_DURATION}s")
    print(f"Ctrl+C to stop\n")

    volume = get_volume()

    try:
        ch_count = volume.GetChannelCount()
        if ch_count < 2:
            print("Mono device → cannot balance. Exiting.")
            return

        print(f"→ Stereo ({ch_count} channels) detected. Monitoring...\n")

        prev_left = prev_right = None
        fast_until = 0.0

        while True:
            now = time.time()
            interval = FAST_INTERVAL if now < fast_until else SLOW_INTERVAL
            mode = "FAST" if now < fast_until else "slow"

            try:
                left  = volume.GetChannelVolumeLevel(0)
                right = volume.GetChannelVolumeLevel(1)
                diff  = abs(left - right)

                if prev_left is None:  # first reading
                    prev_left, prev_right = left, right
                    print(f"[{time.strftime('%H:%M:%S')}] Initial  L: {left:6.2f} dB   R: {right:6.2f} dB")
                    time.sleep(interval)
                    continue

                delta_l = left  - prev_left
                delta_r = right - prev_right

                changed = abs(delta_l) > 0.15 or abs(delta_r) > 0.15

                # ─── Smart sync logic ───────────────────────────────────────
                if diff > TOLERANCE_DB and changed:
                    ts = time.strftime("%H:%M:%S")

                    if abs(delta_l) > abs(delta_r) + DELTA_THRESHOLD:
                        # Left was adjusted more → sync right to new left
                        target = left
                        adjusted = "LEFT"
                        sync_side = "right"
                    elif abs(delta_r) > abs(delta_l) + DELTA_THRESHOLD:
                        # Right was adjusted more → sync left to new right
                        target = right
                        adjusted = "RIGHT"
                        sync_side = "left"
                    else:
                        # Both changed similarly → probably master or bulk change
                        target = (left + right) / 2
                        adjusted = "both/master"
                        sync_side = "both"

                    print(f"[{ts}] {mode}  L:{left:6.2f} R:{right:6.2f}  "
                          f"ΔL:{delta_l:+5.2f} ΔR:{delta_r:+5.2f}  "
                          f"→ {adjusted} adjusted → syncing {sync_side} to {target:6.2f} dB")

                    volume.SetChannelVolumeLevel(0, target, None)
                    volume.SetChannelVolumeLevel(1, target, None)

                    # Trigger fast mode
                    fast_until = now + FAST_DURATION

                elif changed:
                    print(f"[{ts}] {mode}  Small change detected, but still balanced")

                prev_left, prev_right = left, right

            except Exception as e:
                print(f"Error: {e}")
                time.sleep(2)

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\nStopped.")
    except Exception as e:
        print("Fatal error:", e)


if __name__ == "__main__":
    print("Run as Administrator!\n")
    adaptive_smart_balance()