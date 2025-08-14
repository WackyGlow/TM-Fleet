from datetime import datetime

class MultipartMessageBuffer:
    """Handles buffering and reassembly of multipart AIS messages."""

    def __init__(self):
        self.buffer = {}

    def add_fragment(self, line, total_fragments, fragment_number, message_id, channel):
        """Add a fragment to the buffer and return complete message if ready."""
        # Create unique key for this multipart message
        buffer_key = f"{message_id}_{channel}" if message_id else f"no_id_{channel}_{total_fragments}"

        if buffer_key not in self.buffer:
            self.buffer[buffer_key] = {
                'fragments': {},
                'total': total_fragments,
                'timestamp': datetime.now()
            }

        # Store this fragment
        self.buffer[buffer_key]['fragments'][fragment_number] = line

        # Check if we have all fragments
        if len(self.buffer[buffer_key]['fragments']) == total_fragments:
            # We have all fragments - reassemble
            fragments = self.buffer[buffer_key]['fragments']

            # Sort fragments by fragment number and create list
            sorted_fragments = []
            for i in range(1, total_fragments + 1):
                if i in fragments:
                    sorted_fragments.append(fragments[i])
                else:
                    print(f"⚠️ Missing fragment {i} for message {buffer_key}")
                    return None

            # Clean up the buffer
            del self.buffer[buffer_key]

            print(f"✅ Assembled multipart message {buffer_key} ({total_fragments} parts)")
            return sorted_fragments
        else:
            fragments_received = len(self.buffer[buffer_key]['fragments'])
            print(f"🔄 Buffering fragment {fragment_number}/{total_fragments} for {buffer_key} (have {fragments_received}/{total_fragments})")
            return None

    def cleanup_old_fragments(self, max_age_seconds=60):
        """Clean up old incomplete multipart messages."""
        current_time = datetime.now()
        keys_to_remove = []

        for key, data in self.buffer.items():
            if (current_time - data['timestamp']).total_seconds() > max_age_seconds:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            fragments_count = len(self.buffer[key]['fragments'])
            total_expected = self.buffer[key]['total']
            print(f"🧹 Cleaning up incomplete message {key} ({fragments_count}/{total_expected} fragments)")
            del self.buffer[key]

    def get_stats(self):
        """Get buffer statistics."""
        return {
            'buffered_message_count': len(self.buffer),
            'buffered_messages': {k: f"{len(v['fragments'])}/{v['total']}" for k, v in self.buffer.items()}
        }