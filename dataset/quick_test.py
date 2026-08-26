import json
import requests
from email.message import EmailMessage
from pathlib import Path

DATASET = Path("phishing and benign email dataset.jsonl")

# Read dataset
with open(DATASET, "r", encoding="utf-8") as f:
    emails = [json.loads(line) for line in f if line.strip()]

# Select 5 phishing and 5 benign emails
phishing = [e for e in emails if e.get("label") == "phishing"][:5]
benign = [e for e in emails if e.get("label") == "benign"][:5]

test_emails = phishing + benign

print(f"Total emails in dataset: {len(emails)}")
print(f"Testing {len(phishing)} phishing + {len(benign)} benign emails\n")

correct_count = 0

for i, data in enumerate(test_emails, 1):

    msg = EmailMessage()

    msg["Subject"] = data.get("subject", "")
    msg["From"] = data.get(
        "spoofed_sender",
        "unknown@example.com"
    )
    msg["To"] = "test@example.com"

    msg.set_content(data.get("body", ""))

    filename = f"test_email_{i}.eml"

    # Create temporary EML file
    with open(filename, "wb") as f:
        f.write(bytes(msg))

    actual = data.get("label", "").upper()

    print("=" * 60)
    print(f"EMAIL {i}")
    print("=" * 60)
    print("Actual:", actual)
    print("Subject:", data.get("subject", ""))
    print("Sender:", data.get("spoofed_sender", ""))

    try:
        # Send EML to FastAPI backend
        with open(filename, "rb") as f:
            response = requests.post(
                "http://localhost:8000/api/analyze",
                files={
                    "file": (
                        filename,
                        f,
                        "message/rfc822"
                    )
                },
                timeout=120
            )

        print("HTTP status:", response.status_code)

        if response.ok:
            result = response.json()

            predicted = result.get(
                "classification",
                "UNKNOWN"
            ).upper()

            risk = result.get(
                "risk_level",
                "UNKNOWN"
            )

            confidence = result.get(
                "confidence",
                "UNKNOWN"
            )

            print("Predicted:", predicted)
            print("Risk:", risk)
            print("Confidence:", confidence)

            # ------------------------------------------------
            # Compare Kaggle label with backend classification
            #
            # Kaggle:
            #   PHISHING / BENIGN
            #
            # Backend:
            #   PHISHING / SUSPICIOUS / MALWARE / LEGITIMATE
            # ------------------------------------------------

            is_correct = False

            if actual == "PHISHING":
                # Any threat classification counts as detecting
                # the phishing email.
                is_correct = predicted in [
                    "PHISHING",
                    "SUSPICIOUS",
                    "MALWARE"
                ]

            elif actual == "BENIGN":
                # A benign email should be classified as legitimate.
                is_correct = predicted == "LEGITIMATE"

            if is_correct:
                print("Result: CORRECT")
                correct_count += 1
            else:
                print("Result: INCORRECT")

        else:
            print("Backend returned an error:")
            print(response.text)

    except requests.exceptions.ConnectionError:
        print("\nERROR: Could not connect to your FastAPI backend.")
        print("Make sure the backend is running on port 8000.")

    except requests.exceptions.Timeout:
        print("\nERROR: Backend took too long to respond.")

    except Exception as e:
        print("\nERROR:", e)


# ------------------------------------------------------------
# FINAL RESULTS
# ------------------------------------------------------------

total_tested = len(test_emails)
incorrect_count = total_tested - correct_count

print("\n" + "=" * 60)
print("FINAL RESULTS")
print("=" * 60)

print(f"Emails tested: {total_tested}")
print(f"Correct predictions: {correct_count}")
print(f"Incorrect predictions: {incorrect_count}")

if total_tested > 0:
    accuracy = (correct_count / total_tested) * 100
    print(f"Binary threat-detection accuracy: {accuracy:.2f}%")

print("\nInterpretation:")
print("PHISHING → PHISHING/SUSPICIOUS/MALWARE = Threat detected")
print("BENIGN → LEGITIMATE = Correctly identified as benign")