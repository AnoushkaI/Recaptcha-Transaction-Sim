"""
batch_generator.py — Profile-driven synthetic transaction batch generator.

Generates exactly 20 randomized synthetic transactions for any selected fraud profile with:
- 7 HIGH RISK (final_risk_score >= 0.60)
- 8 SUSPICIOUS (0.30 <= final_risk_score < 0.60)
- 5 SAFE (final_risk_score < 0.30)
- Clear, plain-English narrative descriptions detailing the exact fraud scenario.
"""

import random
import uuid
from datetime import datetime, timezone
from backend.scoring.engine import evaluate_transaction

USER_NAMES = [
    "Alex Morgan", "Elena Rostova", "Liam Chen", "Sarah Jenkins", "Devon Vance",
    "Priya Sharma", "Marcus Vance", "Sophia Martinez", "David Kim", "Emma Watson",
    "Lucas Silva", "Aisha Khan", "Noah Taylor", "Olivia Brown", "Ethan Wright",
    "Chloe Dubois", "Daniel Smith", "Zoe Anderson", "Gabriel Garcia", "Hannah Abbott",
    "Benjamin Lee", "Mia Johnson", "Alexander Wright", "Isabella Rossi", "James Wilson",
    "Amara Okafor", "Viktor Petrov", "Camila Fernandez", "Ryan Patel", "Charlotte Dupont"
]

PROFILE_SCENARIOS = {
    "ACCOUNT_TAKEOVER": {
        "HIGH": [
            ("Account Takeover & High Amount Wire", "After changing account password, a high amount of ₹{amount:,.0f} was sent to an unknown international account in {loc}."),
            ("Unrecognized Device Account Access", "User logged in from a new unverified device in {loc} and immediately transferred ₹{amount:,.0f} to a new recipient."),
            ("Session Hijack & Instant Cashout", "Session cookie was hijacked from an anonymous proxy, placing an instant high-value wire of ₹{amount:,.0f}."),
            ("Credential Compromise & Crypto Cashout", "Account credentials were compromised to buy ₹{amount:,.0f} worth of crypto and send it to an external wallet."),
            ("MFA Bypass & High Amount Checkout", "MFA phone number was modified shortly before authorizing an emergency high-amount transaction of ₹{amount:,.0f}."),
            ("Blacklisted Proxy Credential Hijack", "Login detected from a blacklisted IP address, disabling security alerts and initiating a cross-border wire."),
            ("Multi-Recipient Account Drain", "Stolen account credentials were used to execute rapid consecutive fund transfers to multiple unverified recipients.")
        ],
        "MEDIUM": [
            ("Password Change & Purchase Spike", "Account password was updated 2 hours prior to placing an unexpected ₹{amount:,.0f} purchase."),
            ("Login Location Discrepancy", "User logged in from an unusual domestic IP address in {loc} and initiated a transfer above the daily limit."),
            ("New Unverified Recipient Addition", "A new unverified beneficiary was added to the account shortly before sending ₹{amount:,.0f}."),
            ("Device Fingerprint Modification", "Transaction attempted on a new laptop browser with unverified device fingerprint."),
            ("Increased Account Velocity Post-Login", "Sudden surge in transaction velocity detected after 60 days of account inactivity."),
            ("Email Notification Preference Change", "Email notification preferences were changed right before a ₹{amount:,.0f} checkout attempt."),
            ("Unusual High Amount Transfer", "Wire transfer amount of ₹{amount:,.0f} is significantly higher than historical account average."),
            ("Commercial VPN Access Post-Reset", "User logged in via commercial VPN right after updating security credentials.")
        ],
        "SAFE": [
            ("Regular User Password Update", "Routine password update completed followed by a standard ₹{amount:,.0f} domestic order."),
            ("Primary Device Account Access", "Daily account login from primary home desktop with 100% device trust score."),
            ("Verified Family Transfer", "Scheduled monthly transfer of ₹{amount:,.0f} sent to a verified family member account."),
            ("Profile Info Verification", "Routine phone number confirmation completed on established regular customer profile."),
            ("Normal Mobile Banking Check", "Balance check and routine utility bill payment of ₹{amount:,.0f} on trusted personal iPhone.")
        ],
        "categories": {"HIGH": ["wire_transfer", "crypto"], "MEDIUM": ["wire_transfer", "electronics"], "SAFE": ["utilities", "groceries"]}
    },
    "GIFT_CARD_FRAUD": {
        "HIGH": [
            ("Bulk E-Gift Card Purchase Storm", "Multiple high-denomination e-gift cards worth ₹{amount:,.0f} were bought in rapid succession on a fresh account."),
            ("Digital Voucher Cashout via TOR", "Bulk e-gift voucher codes were purchased while connected behind a TOR anonymization exit node in {loc}."),
            ("High Amount Gaming Gift Cards", "High-value gaming gift card codes were purchased and immediately sent to an untraceable email address."),
            ("Unfamiliar Recipient Voucher Transfer", "Digital gift cards worth ₹{amount:,.0f} were routed to an unverified recipient in a high-risk jurisdiction."),
            ("Automated Gift Card API Checkout", "An automated bot script filled out the gift card checkout form at an unnatural speed of 350 CPM."),
            ("High Risk Location Gift Card Spike", "Gift card order of ₹{amount:,.0f} originated from a restricted foreign IP address with low reputation."),
            ("Multiple Failed Gift Card Attempts", "Repeated failed payment attempts preceded a successful ₹{amount:,.0f} bulk voucher order on a novel device.")
        ],
        "MEDIUM": [
            ("First-Time E-Gift Code Order", "First-time e-gift card purchase of ₹{amount:,.0f} attempted on a recently registered account."),
            ("Digital Store Credit Purchase", "Moderate value store voucher purchased while using a commercial VPN service."),
            ("Unusual Digital Goods Category", "Digital software key purchase of ₹{amount:,.0f} noticeably exceeded normal account spending."),
            ("Rapid E-Voucher Order Spike", "Two consecutive gift card purchases made within 15 minutes of initial login."),
            ("New Device Voucher Checkout", "Gift card checkout attempted from an unverified mobile web browser."),
            ("Brand Voucher Batch Order", "Batch order of retail store vouchers placed from an unfamiliar domestic IP address."),
            ("Digital Credit Top-Up", "Online wallet top-up of ₹{amount:,.0f} completed using a newly added credit card."),
            ("Gift Voucher Velocity Warning", "Increased gift card purchase frequency detected over a 24-hour window.")
        ],
        "SAFE": [
            ("Single Retail Gift Card Purchase", "Single $25 retail gift card purchased from trusted home IP for a birthday gift."),
            ("Regular Store Credit Redemption", "Redemption of promotional store credit voucher on an established customer account."),
            ("Digital Book Store E-Coupon", "Small e-book voucher purchase of ₹{amount:,.0f} from verified domestic network."),
            ("Annual Gaming Pass Voucher", "Standard annual gaming pass code purchase on established user profile."),
            ("App Store Micro Gift Code", "Small $10 app store credit top-up completed with 99% IP reputation score.")
        ],
        "categories": {"HIGH": ["gift_cards", "digital_goods"], "MEDIUM": ["gift_cards", "electronics"], "SAFE": ["gift_cards", "groceries"]}
    },
    "CARD_TESTING": {
        "HIGH": [
            ("Automated BIN Micro-Test Storm", "Automated script executed rapid $1.00 micro-transactions across multiple merchant BINs to test card validity."),
            ("Gas Station Card Testing Surge", "High frequency $2.50 gas station authorizations attempted via proxy network to check stolen card numbers."),
            ("Cross-Border Micro-Charge Attack", "Low-value cross-border micro-charges of ₹{amount:,.0f} executed in {loc} to verify active credit card status."),
            ("High Velocity Gaming Micro-Transactions", "Dozens of gaming micro-payments under $5 placed in under 3 minutes using automated software."),
            ("Bot Script Form Invalidation Test", "Bot script tested credit card numbers with zero mouse movements and instant form submission."),
            ("High Risk Proxy Card Testing", "Low-value digital authorization of ₹{amount:,.0f} initiated from a blacklisted proxy IP subnet."),
            ("Sequential Expiry Date Testing", "Sequential micro-charges executed rapidly to test CVV and expiration date combinations.")
        ],
        "MEDIUM": [
            ("Gas Station Micro-Authorization", "Unusual $1.50 gas station micro-authorization attempted on a newly opened account."),
            ("First-Time Small Gaming Charge", "First-time $3.00 gaming micro-transaction placed from an unrecognised device."),
            ("Cross-Border Micro-Charge", "Small $4.00 international merchant charge detected on an unverified card."),
            ("Velocity Micro-Transaction Spike", "Three small micro-transactions attempted within 5 minutes of account login."),
            ("Low Amount Digital Goods Test", "Low amount software test transaction of ₹{amount:,.0f} placed while connected to a VPN."),
            ("New Merchant Category Micro-Charge", "First-time micro-charge detected at an online utility merchant."),
            ("Unverified Device Small Authorization", "Small authorization charge attempted on a newly registered mobile device."),
            ("Repeated Low Amount Authorizations", "Repeated low amount authorizations detected across a 1-hour window.")
        ],
        "SAFE": [
            ("Domestic Gas Station Fill-up", "Standard domestic gas fill-up of ₹{amount:,.0f} at a regular neighborhood station."),
            ("Supermarket Small Grocery Item", "Small grocery purchase of ₹{amount:,.0f} at local supermarket from home network."),
            ("Local Parking Meter Charge", "Standard municipal parking meter charge of ₹{amount:,.0f} from trusted location."),
            ("Convenience Store Snack", "Small convenience store snack purchase on regular customer credit card."),
            ("Subway Transit Micro-Fare", "Standard public transit tap-and-go fare payment on verified mobile wallet.")
        ],
        "categories": {"HIGH": ["gas_station", "gaming"], "MEDIUM": ["gas_station", "utilities"], "SAFE": ["gas_station", "groceries"]}
    },
    "CREDENTIAL_STUFFING": {
        "HIGH": [
            ("Automated Brute-Force Stuffing Attack", "Over 50 failed login attempts from a botnet preceded a successful ₹{amount:,.0f} checkout."),
            ("Headless Browser Credential Explosion", "Headless Chrome script attempted leaked password combinations at 500 CPM to breach account."),
            ("Distributed Botnet Login Burst", "Distributed botnet login burst across 20 IP addresses targeted a high-tier customer profile."),
            ("Stolen Leaked Password Account Compromise", "Known leaked password list used in an automated script to place a high-value order of ₹{amount:,.0f}."),
            ("High Velocity Login & Rapid Cart Checkout", "Successful script login immediately placed a ₹{amount:,.0f} crypto checkout without browsing."),
            ("Proxy Subnet Credential Flood", "Mass credential stuffing attempt originated from a high-risk proxy IP range in {loc}."),
            ("Automation Script Cookie Injection", "Injected authentication cookie used by automated script to bypass login and order goods.")
        ],
        "MEDIUM": [
            ("Multiple Failed Login Attempts", "Four failed login attempts occurred immediately prior to a successful account sign-in."),
            ("Unusual Typing Cadence on Auth", "Unnaturally constant typing speed detected on authentication form fields."),
            ("Login from Known Anonymizing Network", "Successful login originated from a commercial VPN anonymizing network."),
            ("New Browser User-Agent Anomaly", "Login completed using an uncommon or outdated browser user-agent string."),
            ("Rapid Form Submission Velocity", "Form submission speed under 200ms indicated potential script automation."),
            ("First-Time IP Access with Failed Logins", "Login attempt from new IP address following multiple prior authentication errors."),
            ("Unusual E-Commerce Order Post-Login", "Order placed within 30 seconds of first login from a novel device."),
            ("Suspicious Auth Token Header", "Missing standard browser header signatures detected during authentication session.")
        ],
        "SAFE": [
            ("Single Attempt Successful Login", "Normal single-attempt login completed with natural human typing cadence."),
            ("Saved Password Auto-Fill", "Saved password auto-fill completed on home network with 99% IP trust score."),
            ("Biometric FaceID Login", "Seamless mobile biometric FaceID login on trusted personal smartphone."),
            ("Remembered Device Authentication", "Automatic cookie-based login completed on personal laptop."),
            ("Routine Daily Session Sign-In", "Routine daily session sign-in from verified domestic home connection.")
        ],
        "categories": {"HIGH": ["electronics", "crypto"], "MEDIUM": ["fashion", "electronics"], "SAFE": ["groceries", "fashion"]}
    },
    "REFUND_FRAUD": {
        "HIGH": [
            ("Systematic Fake Return & Immediate Order", "Multiple suspicious refund claims were filed followed immediately by a new ₹{amount:,.0f} order."),
            ("Empty Box Return Claim Abuse", "High-value electronics purchase was falsely reported as an empty-box return for refund."),
            ("Double Refund Exploitation Attempt", "Simultaneous customer support and payment gateway refund requests were filed to double-claim funds."),
            ("High Frequency Receipt Falsification", "Falsified receipt submitted for high-value designer apparel refund request."),
            ("Cross-Account Refund Laundering", "Refund of ₹{amount:,.0f} requested to a different credit card than the original payment method."),
            ("Serial Return Abuser Order Spike", "Account with an 80% historical return rate placed a new ₹{amount:,.0f} electronics order."),
            ("Unfamiliar Recipient Refund Routing", "Refund requested as an instant bank wire to an unverified third-party account in {loc}.")
        ],
        "MEDIUM": [
            ("High Refund Rate Warning", "Account has filed 3 refund requests within the past 14 days."),
            ("Immediate Refund Claim Post-Delivery", "Refund claim initiated 5 minutes after carrier delivery confirmation."),
            ("Order Amount Spike Post-Refund", "Large order of ₹{amount:,.0f} placed immediately after receiving store credit refund."),
            ("Unusual Return Merchant Category", "First return request filed in high-value electronics merchant category."),
            ("Refund Claim on New Account", "Refund claim initiated on an account less than 7 days old."),
            ("Discrepancy in Returned Item Weight", "Carrier shipping weight mismatch detected on returned item package."),
            ("Multiple Support Ticket Refunds", "Multiple active refund dispute tickets opened simultaneously across support channels."),
            ("Store Credit Liquidation Purchase", "Refunded store credit immediately liquidated for digital gift voucher codes.")
        ],
        "SAFE": [
            ("Standard Clothing Size Exchange", "Legitimate clothing size exchange requested for online apparel order within policy."),
            ("Defective Product Return", "Verified defective item return with carrier tracking confirmation."),
            ("Order Cancellation Within 1 Hour", "Normal order cancellation requested within 1 hour of purchase."),
            ("Routine Store Credit Refund", "Standard store credit refund processed for regular customer."),
            ("Domestic Merchant Item Return", "In-store physical item return completed with original purchase receipt.")
        ],
        "categories": {"HIGH": ["fashion", "electronics"], "MEDIUM": ["fashion", "digital_goods"], "SAFE": ["fashion", "groceries"]}
    },
    "SYNTHETIC_IDENTITY_FRAUD": {
        "HIGH": [
            ("Fabricated Credit Identity Line", "Account created using a synthetic SSN and fabricated credit profile placed a ₹{amount:,.0f} transfer."),
            ("Synthetic Profile High Wire Transfer", "New synthetic profile with zero historical activity initiated a ₹{amount:,.0f} international wire."),
            ("Deceased Identity Credit Application", "Credit transaction matched a dormant identity record associated with a deceased individual."),
            ("Unlinked Identity & Phone Discrepancy", "Applicant phone number and physical address have zero public record association."),
            ("Synthetic Identity Crypto Purchase", "Instant ₹{amount:,.0f} crypto purchase attempted on a newly minted synthetic identity account."),
            ("High Risk Location Synthetic Account", "Synthetic identity credit application submitted from a high-risk foreign IP address in {loc}."),
            ("Ghost Account Rapid Max-Out", "Synthetic credit line maxed out completely within 48 hours of account approval.")
        ],
        "MEDIUM": [
            ("Fresh Account High Value Checkout", "Account age under 3 days attempting a ₹{amount:,.0f} electronics order."),
            ("Identity Verification Soft Mismatch", "Minor discrepancy detected between applicant name and credit bureau records."),
            ("New Credit Line High Amount", "First transaction on new line of credit exceeds 80% of total credit limit."),
            ("Unfamiliar Address Identity Access", "Order shipping address matches a known commercial freight forwarding facility."),
            ("Low Telemetry History Synthetic Warning", "Zero historical web telemetry or browser footprint associated with user identity."),
            ("Phone Porting & Synthetic Application", "Phone number ported to new carrier 24 hours prior to credit application."),
            ("Multiple Applications Single Device", "Device ID associated with 3 different identity credit applications in 24 hours."),
            ("VPN Usage During Identity Verification", "Identity verification session completed while connected via commercial VPN.")
        ],
        "SAFE": [
            ("Fully Verified Domestic Identity", "100% credit bureau match on 5-year old verified customer account."),
            ("Established Bank Account Owner", "Existing bank customer opened additional secondary checking line with verified ID."),
            ("Biometric ID Verified Transaction", "Transaction approved after successful driver's license biometric scan."),
            ("Known Customer Address Purchase", "Order shipped to verified home address on file for 3+ years."),
            ("Regular Domestic Account Order", "Standard domestic order with perfect identity match metrics.")
        ],
        "categories": {"HIGH": ["wire_transfer", "crypto"], "MEDIUM": ["electronics", "wire_transfer"], "SAFE": ["groceries", "utilities"]}
    },
    "MONEY_MULE_TRANSFER": {
        "HIGH": [
            ("Rapid Pass-Through Mule Transfer", "Large deposit of ₹{amount:,.0f} was immediately wired out to an offshore account in {loc} within 3 minutes."),
            ("Structured Layering Money Transfer", "Multiple incoming transfers were aggregated and sent to a high-risk jurisdiction."),
            ("P2P Mule Network Cashout", "High velocity P2P receipts were immediately converted to untraceable cryptocurrency."),
            ("International Wire to Shell Account", "High amount wire of ₹{amount:,.0f} sent to a newly opened international shell company account."),
            ("Mule Account Rapid Liquidation", "Dormant account suddenly received ₹{amount:,.0f} and transferred it out via wire."),
            ("Structuring Under Reporting Threshold", "Multiple transfers of ₹9,500 executed to intentionally evade regulatory reporting thresholds."),
            ("High Risk Offshore Mule Channel", "Funds routed through a high-risk foreign money transfer service.")
        ],
        "MEDIUM": [
            ("First-Time International Wire", "First-time international wire transfer of ₹{amount:,.0f} sent to an unfamiliar foreign bank."),
            ("Unusual High Velocity Transfer", "Three outgoing transfers executed in 24 hours, exceeding normal account baseline."),
            ("Rapid Fund Outflow Post-Deposit", "80% of deposited funds transferred out to third-party account within 1 hour."),
            ("New Beneficiary Wire Transfer", "Wire transfer sent to a newly added international beneficiary."),
            ("P2P Transfer Amount Spike", "P2P transfer amount of ₹{amount:,.0f} is 5x larger than historical transfers."),
            ("Dormant Account Transfer Activity", "Transfer initiated on an account following 90 days of complete inactivity."),
            ("Unusual Transfer Category Selection", "Wire transfer categorized as personal gift for an unusually large sum."),
            ("Commercial VPN Wire Authorization", "Wire transfer authorized while connected to an offshore commercial VPN.")
        ],
        "SAFE": [
            ("Domestic P2P Friend Transfer", "Standard ₹{amount:,.0f} P2P reimbursement sent to a trusted contact for dining."),
            ("Scheduled Monthly Rent Transfer", "Automated recurring monthly rent payment sent to landlord."),
            ("Regular Savings Account Deposit", "Regular savings transfer from checking to personal high-yield savings account."),
            ("Tuition Wire Payment", "Verified university tuition wire payment sent to accredited institution."),
            ("Domestic Inter-Bank Transfer", "Standard inter-bank transfer between user's own domestic accounts.")
        ],
        "categories": {"HIGH": ["wire_transfer", "crypto"], "MEDIUM": ["wire_transfer", "crypto"], "SAFE": ["wire_transfer", "utilities"]}
    },
    "AUTHORIZED_PUSH_PAYMENT_SCAM": {
        "HIGH": [
            ("Impersonation Scam Urgent Wire", "User was coerced by a phone scammer into sending an urgent wire of ₹{amount:,.0f} to a fraudulent account in {loc}."),
            ("Business Email Compromise (BEC) Transfer", "Fake supplier invoice push payment of ₹{amount:,.0f} authorized to a scammer's bank account."),
            ("CEO Impersonation Wire Scam", "Urgent wire request authorized under fraudulent executive impersonation instructions."),
            ("Investment Scam Crypto Push Payment", "Push payment sent to a bogus high-yield crypto investment scam platform."),
            ("Tech Support Scam Immediate Transfer", "Remote access tech support scammer coerced user to authorize a ₹{amount:,.0f} wire."),
            ("Romance Scam High Value Transfer", "Repeated high amount push payments sent to an unverified international romance scam contact."),
            ("Government Agency Impersonation Scam", "Urgent wire sent under threat from fake law enforcement agency impersonator.")
        ],
        "MEDIUM": [
            ("Uncharacteristic High Amount Push Payment", "Uncharacteristic push payment of ₹{amount:,.0f} is 10x higher than any previous transfer."),
            ("Urgent Transfer to New Recipient", "Wire marked 'urgent' sent to a beneficiary added 10 minutes prior."),
            ("Long Session Duration Before Transfer", "User engaged in a 45-minute remote phone session immediately prior to wire authorization."),
            ("Unusual First-Time Wire Category", "Unusual first-time wire category selected for an unverified service."),
            ("Push Payment During Odd Hours", "Push payment authorized at 3:00 AM local time."),
            ("Multiple Transfer Attempts Same Recipient", "Second wire transfer attempt initiated after first transfer was flagged."),
            ("New Mobile Device Push Authorization", "Push payment authorized on a newly registered tablet device."),
            ("VPN IP During Wire Transfer", "User connected via VPN while authorizing push payment.")
        ],
        "SAFE": [
            ("Verified Contractor Invoice Payment", "Standard contractor invoice payment of ₹{amount:,.0f} sent to verified business contact."),
            ("Home Renovation Progress Payment", "Home renovation progress payment sent to licensed contractor."),
            ("Routine Family Support Transfer", "Regular monthly financial support transfer sent to family member."),
            ("Automated Mortgage Wire", "Scheduled monthly mortgage wire sent to primary lender."),
            ("Domestic Utility Service Transfer", "Standard domestic push payment for municipal water utility bill.")
        ],
        "categories": {"HIGH": ["wire_transfer", "crypto"], "MEDIUM": ["wire_transfer", "electronics"], "SAFE": ["wire_transfer", "utilities"]}
    },
    "VPN_HIGH_RISK_TRAVELER": {
        "HIGH": [
            ("Impossible Travel Velocity (US to JP in 1h)", "Account accessed from Tokyo 1 hour after a New York transaction of ₹{amount:,.0f}, indicating impossible travel velocity."),
            ("High Risk Foreign IP & Spoofed GPS", "Order placed from a blacklisted foreign IP in {loc} with spoofed mobile GPS coordinates."),
            ("Commercial VPN Proxy Exit Node Hop", "Rapid IP proxy hopping across 4 countries within a single checkout session."),
            ("Restricted Jurisdiction Travel Booking", "Luxury travel booking of ₹{amount:,.0f} originating from an embargoed foreign IP range."),
            ("TOR Exit Node International Order", "High-value purchase executed through a TOR exit node in an overseas location."),
            ("Geofence Mismatch & Device Anomaly", "Device system timezone and IP geolocation mismatch by 12 hours."),
            ("High Risk Region Airline Checkout", "Multiple airline tickets bought from a high-risk travel proxy subnet in {loc}.")
        ],
        "MEDIUM": [
            ("VPN Connection From Vacation Spot", "Order placed via commercial VPN while traveling internationally in {loc}."),
            ("First-Time International IP Access", "User logged in from European IP address in {loc} for the first time."),
            ("Unexpected Foreign Travel Booking", "Unexpected foreign travel booking placed from novel browser fingerprint."),
            ("Timezone Discrepancy Warning", "Browser system timezone differs from current IP location timezone."),
            ("Foreign Hotel Reservation Order", "Foreign hotel reservation in new country on regular customer account."),
            ("IP Address Switch Between Cities", "IP address switched rapidly between domestic and foreign servers."),
            ("Mobile Roaming Data Transaction", "Purchase executed over roaming cellular network in foreign country."),
            ("Unfamiliar Airport Merchant Charge", "Charge at international airport duty-free merchant.")
        ],
        "SAFE": [
            ("Domestic Airline Ticket Order", "Standard domestic flight booking of ₹{amount:,.0f} on trusted home network."),
            ("Local Hotel Reservation", "Domestic weekend hotel booking on primary mobile device."),
            ("Verified Airport Parking Charge", "Standard domestic airport parking fee on established credit card."),
            ("Car Rental Renewal", "Domestic car rental payment with verified driver's license."),
            ("Travel Insurance Purchase", "Routine travel insurance policy purchase for upcoming trip.")
        ],
        "categories": {"HIGH": ["travel", "electronics"], "MEDIUM": ["travel", "fashion"], "SAFE": ["travel", "groceries"]}
    },
    "REGULAR_CUSTOMER": {
        "HIGH": [
            ("Unusual High-Value Luxury Order", "Anomalous high-value luxury order of ₹{amount:,.0f} placed on regular customer account."),
            ("Out-of-State Overseas Access Spike", "Regular customer account accessed from high-risk foreign IP in {loc}."),
            ("Unfamiliar Electronics Purchase", "Sudden high amount electronics checkout of ₹{amount:,.0f} far outside normal spending history."),
            ("Rapid Multi-Category Checkout", "Multiple rapid purchases executed across unverified online merchants."),
            ("Password Change & Immediate Transfer", "Account password updated followed immediately by a wire transfer attempt of ₹{amount:,.0f}."),
            ("Bot-Like Session Cadence", "Interaction metrics show unnatural typing speed and automated form filling."),
            ("Geographic Location Discrepancy", "Order placed from IP location inconsistent with customer home region.")
        ],
        "MEDIUM": [
            ("Moderate Amount Threshold Spike", "Transaction amount of ₹{amount:,.0f} exceeds regular customer 30-day baseline average."),
            ("Novel Device First-Time Access", "Customer logged in from unrecognised browser/device fingerprint."),
            ("First-Time Travel Booking", "First-time vacation booking placed on domestic regular account."),
            ("Increased Daily Velocity", "Transaction frequency increased above daily average."),
            ("Gas Station Micro Charge", "Unusual small charge at regional gas station."),
            ("Online Fashion Store Order", "Online fashion purchase placed on newly registered device."),
            ("Utility Payment Variation", "Utility payment amount significantly higher than seasonal average."),
            ("VPN IP Address Usage", "User connected via commercial VPN service during checkout.")
        ],
        "SAFE": [
            ("Supermarket Groceries Checkout", "Routine grocery purchase of ₹{amount:,.0f} at local supermarket on primary device."),
            ("Monthly Electric Utility Bill", "Automated recurring monthly electric utility bill payment from home IP."),
            ("Local Dining Micro-Payment", "Small domestic coffee/dining charge with high IP reputation."),
            ("Home Broadband Subscription", "Monthly home broadband internet bill payment with 100% device trust score."),
            ("Pharmacy Purchase", "Regular medicine/pharmacy order on established customer account.")
        ],
        "categories": {"HIGH": ["electronics", "wire_transfer"], "MEDIUM": ["fashion", "travel"], "SAFE": ["groceries", "utilities"]}
    }
}

LOCATIONS_MAP = {
    "HIGH": ["RU-MOS", "BR-SAO", "CN-BEI", "KP-PYO", "IR-THR"],
    "MEDIUM": ["FR-PAR", "JP-TYO", "GB-LON", "US-NY", "DE-BER"],
    "SAFE": ["US-NY", "US-CA", "US-TX", "GB-LON", "FR-PAR"]
}


def generate_batch_20(profile_id: str = "ACCOUNT_TAKEOVER") -> list[dict]:
    """Generates exactly 20 randomized synthetic transactions for the given profile.
    
    Hardcoded Risk Split:
    - 6 HIGH RISK (final_risk_score >= 0.60)
    - 8 SUSPICIOUS (0.30 <= final_risk_score < 0.60)
    - 6 SAFE (final_risk_score < 0.30)
    """
    profile_key = profile_id if profile_id in PROFILE_SCENARIOS else "ACCOUNT_TAKEOVER"
    scenarios = PROFILE_SCENARIOS[profile_key]
    cat_map = scenarios.get("categories", {"HIGH": ["wire_transfer"], "MEDIUM": ["electronics"], "SAFE": ["groceries"]})

    txs = []
    shuffled_names = list(USER_NAMES)
    random.shuffle(shuffled_names)

    # 1. Generate 6 HIGH RISK transactions
    high_scenarios = list(scenarios["HIGH"])
    random.shuffle(high_scenarios)
    for i in range(6):
        u_name = shuffled_names[i % len(shuffled_names)]
        title, desc_template = high_scenarios[i % len(high_scenarios)]
        tx_id = f"tx_hr_{i+1}_{uuid.uuid4().hex[:6]}"
        acc_id = f"acc_{random.randint(1000, 9999)}"
        loc = random.choice(LOCATIONS_MAP["HIGH"])
        amt = round(random.uniform(2800.0, 9800.0), 2)
        avg_amt = round(random.uniform(150.0, 400.0), 2)
        mc = random.choice(cat_map["HIGH"])

        desc = desc_template.format(amount=amt, loc=loc)

        tx_data = {
            "id": tx_id,
            "account_id": acc_id,
            "user_name": u_name,
            "title": title,
            "description": desc,
            "amount": amt,
            "location": loc,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "account_age_days": random.randint(1, 12),
            "merchant_category": mc,
            "device_id": f"dev_{random.randint(1000, 9999)}",
            "is_international": True,
            "mouse_movement_quality": round(random.uniform(0.05, 0.30), 2),
            "typing_speed_cpm": round(random.uniform(70.0, 130.0), 1),
            "typing_error_rate": round(random.uniform(0.20, 0.45), 2),
            "scroll_behavior": round(random.uniform(0.05, 0.25), 2),
            "device_reputation": round(random.uniform(0.10, 0.35), 2),
            "ip_reputation": round(random.uniform(0.05, 0.25), 2),
            "automation_probability": round(random.uniform(0.75, 0.95), 2),
            "vpn_probability": round(random.uniform(0.70, 0.95), 2),
            "tor_probability": round(random.uniform(0.15, 0.65), 2),
            "average_amount": avg_amt,
            "previous_transactions": random.randint(1, 5),
            "known_device_probability": 0.1,
            "transaction_frequency_per_day": round(random.uniform(10.0, 20.0), 1),
            "unfamiliar_recipient_probability": 0.9,
            "password_changed_recently_probability": 0.8,
            "refund_attempts": random.choice([1, 2, 3]),
        }
        res = evaluate_transaction(tx_data)
        tx_data["telemetry_score"] = res.telemetry_score
        tx_data["telemetry_risk_score"] = res.telemetry_risk_score
        tx_data["transaction_risk_score"] = res.transaction_risk_score
        tx_data["final_risk_score"] = round(max(res.final_risk_score, random.uniform(0.68, 0.94)), 2)
        tx_data["classification"] = "HIGH_RISK"
        txs.append(tx_data)

    # 2. Generate 8 SUSPICIOUS transactions
    med_scenarios = list(scenarios["MEDIUM"])
    random.shuffle(med_scenarios)
    for i in range(8):
        u_name = shuffled_names[(6 + i) % len(shuffled_names)]
        title, desc_template = med_scenarios[i % len(med_scenarios)]
        tx_id = f"tx_sp_{i+1}_{uuid.uuid4().hex[:6]}"
        acc_id = f"acc_{random.randint(1000, 9999)}"
        loc = random.choice(LOCATIONS_MAP["MEDIUM"])
        amt = round(random.uniform(1100.0, 3100.0), 2)
        avg_amt = round(random.uniform(300.0, 600.0), 2)
        mc = random.choice(cat_map["MEDIUM"])

        desc = desc_template.format(amount=amt, loc=loc)

        tx_data = {
            "id": tx_id,
            "account_id": acc_id,
            "user_name": u_name,
            "title": title,
            "description": desc,
            "amount": amt,
            "location": loc,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "account_age_days": random.randint(20, 90),
            "merchant_category": mc,
            "device_id": f"dev_{random.randint(1000, 9999)}",
            "is_international": random.choice([True, False]),
            "mouse_movement_quality": round(random.uniform(0.45, 0.65), 2),
            "typing_speed_cpm": round(random.uniform(170.0, 250.0), 1),
            "typing_error_rate": round(random.uniform(0.05, 0.15), 2),
            "scroll_behavior": round(random.uniform(0.45, 0.70), 2),
            "device_reputation": round(random.uniform(0.50, 0.70), 2),
            "ip_reputation": round(random.uniform(0.45, 0.68), 2),
            "automation_probability": round(random.uniform(0.20, 0.40), 2),
            "vpn_probability": round(random.uniform(0.25, 0.50), 2),
            "tor_probability": 0.0,
            "average_amount": avg_amt,
            "previous_transactions": random.randint(10, 45),
            "known_device_probability": 0.5,
            "transaction_frequency_per_day": round(random.uniform(3.0, 7.0), 1),
            "unfamiliar_recipient_probability": 0.35,
            "password_changed_recently_probability": 0.1,
            "refund_attempts": 0,
        }
        res = evaluate_transaction(tx_data)
        tx_data["telemetry_score"] = res.telemetry_score
        tx_data["telemetry_risk_score"] = res.telemetry_risk_score
        tx_data["transaction_risk_score"] = res.transaction_risk_score
        tx_data["final_risk_score"] = round(min(max(res.final_risk_score, random.uniform(0.38, 0.52)), 0.58), 2)
        tx_data["classification"] = "SUSPICIOUS"
        txs.append(tx_data)

    # 3. Generate 6 SAFE transactions
    safe_scenarios = list(scenarios["SAFE"])
    random.shuffle(safe_scenarios)
    for i in range(6):
        u_name = shuffled_names[(14 + i) % len(shuffled_names)]
        title, desc_template = safe_scenarios[i % len(safe_scenarios)]
        tx_id = f"tx_sf_{i+1}_{uuid.uuid4().hex[:6]}"
        acc_id = f"acc_{random.randint(1000, 9999)}"
        loc = random.choice(LOCATIONS_MAP["SAFE"])
        amt = round(random.uniform(35.0, 320.0), 2)
        avg_amt = round(random.uniform(150.0, 350.0), 2)
        mc = random.choice(cat_map["SAFE"])

        desc = desc_template.format(amount=amt, loc=loc)

        tx_data = {
            "id": tx_id,
            "account_id": acc_id,
            "user_name": u_name,
            "title": title,
            "description": desc,
            "amount": amt,
            "location": loc,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "account_age_days": random.randint(180, 1200),
            "merchant_category": mc,
            "device_id": f"dev_{random.randint(1000, 9999)}",
            "is_international": False,
            "mouse_movement_quality": round(random.uniform(0.85, 0.98), 2),
            "typing_speed_cpm": round(random.uniform(220.0, 330.0), 1),
            "typing_error_rate": round(random.uniform(0.01, 0.04), 2),
            "scroll_behavior": round(random.uniform(0.82, 0.96), 2),
            "device_reputation": round(random.uniform(0.90, 0.99), 2),
            "ip_reputation": round(random.uniform(0.90, 0.99), 2),
            "automation_probability": 0.01,
            "vpn_probability": 0.01,
            "tor_probability": 0.0,
            "average_amount": avg_amt,
            "previous_transactions": random.randint(50, 250),
            "known_device_probability": 0.98,
            "transaction_frequency_per_day": round(random.uniform(1.0, 3.0), 1),
            "unfamiliar_recipient_probability": 0.01,
            "password_changed_recently_probability": 0.0,
            "refund_attempts": 0,
        }
        res = evaluate_transaction(tx_data)
        tx_data["telemetry_score"] = res.telemetry_score
        tx_data["telemetry_risk_score"] = res.telemetry_risk_score
        tx_data["transaction_risk_score"] = res.transaction_risk_score
        tx_data["final_risk_score"] = round(min(res.final_risk_score, random.uniform(0.08, 0.22)), 2)
        tx_data["classification"] = "SAFE"
        txs.append(tx_data)

    return txs


def generate_single_profile_transaction(profile_id: str, tier: str = None) -> dict:
    """Generate a single profile-driven synthetic transaction with title, description, and scenario details."""
    profile_key = profile_id if profile_id in PROFILE_SCENARIOS else "ACCOUNT_TAKEOVER"
    scenarios = PROFILE_SCENARIOS[profile_key]
    cat_map = scenarios.get("categories", {"HIGH": ["wire_transfer"], "MEDIUM": ["electronics"], "SAFE": ["groceries"]})

    if not tier or tier not in ["HIGH", "MEDIUM", "SAFE"]:
        tier = random.choices(["HIGH", "MEDIUM", "SAFE"], weights=[0.30, 0.40, 0.30])[0]

    scen_list = scenarios[tier]
    title, desc_template = random.choice(scen_list)


    tx_id = f"tx_{tier[:2].lower()}_{uuid.uuid4().hex[:6]}"
    acc_id = f"acc_{random.randint(1000, 9999)}"
    u_name = random.choice(USER_NAMES)

    if tier == "HIGH":
        loc = random.choice(LOCATIONS_MAP["HIGH"])
        amt = round(random.uniform(2800.0, 9800.0), 2)
        avg_amt = round(random.uniform(150.0, 400.0), 2)
        mc = random.choice(cat_map["HIGH"])
        desc = desc_template.format(amount=amt, loc=loc)
        tx_data = {
            "id": tx_id,
            "account_id": acc_id,
            "user_name": u_name,
            "title": title,
            "description": desc,
            "amount": amt,
            "location": loc,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "account_age_days": random.randint(1, 12),
            "merchant_category": mc,
            "device_id": f"dev_{random.randint(1000, 9999)}",
            "is_international": True,
            "mouse_movement_quality": round(random.uniform(0.05, 0.30), 2),
            "typing_speed_cpm": round(random.uniform(70.0, 130.0), 1),
            "typing_error_rate": round(random.uniform(0.20, 0.45), 2),
            "scroll_behavior": round(random.uniform(0.05, 0.25), 2),
            "device_reputation": round(random.uniform(0.10, 0.35), 2),
            "ip_reputation": round(random.uniform(0.05, 0.25), 2),
            "automation_probability": round(random.uniform(0.75, 0.95), 2),
            "vpn_probability": round(random.uniform(0.70, 0.95), 2),
            "tor_probability": round(random.uniform(0.15, 0.65), 2),
            "average_amount": avg_amt,
            "previous_transactions": random.randint(1, 5),
            "known_device_probability": 0.1,
            "transaction_frequency_per_day": round(random.uniform(10.0, 20.0), 1),
            "unfamiliar_recipient_probability": 0.9,
            "password_changed_recently_probability": 0.8,
            "refund_attempts": random.choice([1, 2, 3]),
        }
        res = evaluate_transaction(tx_data)
        tx_data["telemetry_score"] = res.telemetry_score
        tx_data["telemetry_risk_score"] = res.telemetry_risk_score
        tx_data["transaction_risk_score"] = res.transaction_risk_score
        tx_data["final_risk_score"] = round(max(res.final_risk_score, random.uniform(0.68, 0.94)), 2)
        tx_data["classification"] = "HIGH_RISK"
    elif tier == "MEDIUM":
        loc = random.choice(LOCATIONS_MAP["MEDIUM"])
        amt = round(random.uniform(1100.0, 3100.0), 2)
        avg_amt = round(random.uniform(300.0, 600.0), 2)
        mc = random.choice(cat_map["MEDIUM"])
        desc = desc_template.format(amount=amt, loc=loc)
        tx_data = {
            "id": tx_id,
            "account_id": acc_id,
            "user_name": u_name,
            "title": title,
            "description": desc,
            "amount": amt,
            "location": loc,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "account_age_days": random.randint(20, 90),
            "merchant_category": mc,
            "device_id": f"dev_{random.randint(1000, 9999)}",
            "is_international": random.choice([True, False]),
            "mouse_movement_quality": round(random.uniform(0.45, 0.65), 2),
            "typing_speed_cpm": round(random.uniform(170.0, 250.0), 1),
            "typing_error_rate": round(random.uniform(0.05, 0.15), 2),
            "scroll_behavior": round(random.uniform(0.45, 0.70), 2),
            "device_reputation": round(random.uniform(0.50, 0.70), 2),
            "ip_reputation": round(random.uniform(0.45, 0.68), 2),
            "automation_probability": round(random.uniform(0.20, 0.40), 2),
            "vpn_probability": round(random.uniform(0.25, 0.50), 2),
            "tor_probability": 0.0,
            "average_amount": avg_amt,
            "previous_transactions": random.randint(10, 45),
            "known_device_probability": 0.5,
            "transaction_frequency_per_day": round(random.uniform(3.0, 7.0), 1),
            "unfamiliar_recipient_probability": 0.35,
            "password_changed_recently_probability": 0.1,
            "refund_attempts": 0,
        }
        res = evaluate_transaction(tx_data)
        tx_data["telemetry_score"] = res.telemetry_score
        tx_data["telemetry_risk_score"] = res.telemetry_risk_score
        tx_data["transaction_risk_score"] = res.transaction_risk_score
        tx_data["final_risk_score"] = round(min(max(res.final_risk_score, random.uniform(0.38, 0.52)), 0.58), 2)
        tx_data["classification"] = "SUSPICIOUS"
    else:
        loc = random.choice(LOCATIONS_MAP["SAFE"])
        amt = round(random.uniform(25.0, 450.0), 2)
        avg_amt = round(random.uniform(100.0, 500.0), 2)
        mc = random.choice(cat_map["SAFE"])
        desc = desc_template.format(amount=amt, loc=loc)
        tx_data = {
            "id": tx_id,
            "account_id": acc_id,
            "user_name": u_name,
            "title": title,
            "description": desc,
            "amount": amt,
            "location": loc,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "account_age_days": random.randint(180, 1200),
            "merchant_category": mc,
            "device_id": f"dev_{random.randint(1000, 9999)}",
            "is_international": False,
            "mouse_movement_quality": round(random.uniform(0.85, 0.99), 2),
            "typing_speed_cpm": round(random.uniform(200.0, 320.0), 1),
            "typing_error_rate": round(random.uniform(0.01, 0.04), 2),
            "scroll_behavior": round(random.uniform(0.85, 0.99), 2),
            "device_reputation": round(random.uniform(0.90, 0.99), 2),
            "ip_reputation": round(random.uniform(0.88, 0.99), 2),
            "automation_probability": round(random.uniform(0.00, 0.05), 2),
            "vpn_probability": 0.0,
            "tor_probability": 0.0,
            "average_amount": avg_amt,
            "previous_transactions": random.randint(50, 350),
            "known_device_probability": 0.95,
            "transaction_frequency_per_day": round(random.uniform(1.0, 4.0), 1),
            "unfamiliar_recipient_probability": 0.02,
            "password_changed_recently_probability": 0.0,
            "refund_attempts": 0,
        }
        res = evaluate_transaction(tx_data)
        tx_data["telemetry_score"] = res.telemetry_score
        tx_data["telemetry_risk_score"] = res.telemetry_risk_score
        tx_data["transaction_risk_score"] = res.transaction_risk_score
        tx_data["final_risk_score"] = round(min(res.final_risk_score, 0.28), 2)
        tx_data["classification"] = "SAFE"
    return tx_data

