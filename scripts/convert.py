import json
import csv

def export_logs_to_csv(log_file_path, output_csv_path):
    with open(output_csv_path, mode='w', newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        # Write headers
        writer.writerow(["Timestamp", "Log Type", "Message", "Comment ID", "Sanitized Query", "Category", "Intent", "Energy", "Verdict", "HTTP Status"])

        with open(log_file_path, 'r', encoding='utf-8') as f:
            try:
                logs = json.load(f)
                if not isinstance(logs, list):
                    logs = [logs]
                
                for entry in logs:
                    timestamp = entry.get("timestamp")
                    text_payload = entry.get("textPayload", "")
                    
                    # Check if the log line contains our structured audit JSON
                    if "Lumi Swarm Decision" in text_payload or "Audit event" in text_payload:
                        writer.writerow([timestamp, "Audit Log", text_payload, "", "", "", "", "", "", ""])
                    
                    # Also check if jsonPayload exists (in case some entries have it)
                    elif "jsonPayload" in entry:
                        payload = entry["jsonPayload"]
                        writer.writerow([
                            timestamp,
                            "JSON Payload",
                            payload.get("message", ""),
                            payload.get("comment_id", ""),
                            payload.get("sanitized_query", ""),
                            payload.get("comment_category", ""),
                            payload.get("semiotic_intent", ""),
                            payload.get("energy_level", ""),
                            payload.get("security_verdict", ""),
                            payload.get("http_status", "")
                        ])
                    elif text_payload:
                        # Capture general stdout text payloads
                        writer.writerow([timestamp, "Stdout", text_payload, "", "", "", "", "", "", ""])
                        
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")

    print(f"✅ Audit spreadsheet successfully exported to {output_csv_path}")

export_logs_to_csv('gcp_logs.jsonl', 'audit_report.csv')