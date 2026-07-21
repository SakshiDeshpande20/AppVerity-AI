from __future__ import annotations

from collections import Counter
import hashlib
from typing import Any
import zipfile


MAX_APK_SIZE_BYTES = 200 * 1024 * 1024

SEVERITY_ORDER = {
    "Critical": 0,
    "High": 1,
    "Medium": 2,
    "Review": 3,
    "Common": 4,
}

SEVERITY_POINTS = {
    "Critical": 18,
    "High": 9,
    "Medium": 4,
    "Review": 1,
    "Common": 0,
}

SPECIAL_ACCESS_PERMISSIONS = {
    "SYSTEM_ALERT_WINDOW",
    "REQUEST_INSTALL_PACKAGES",
    "MANAGE_EXTERNAL_STORAGE",
    "PACKAGE_USAGE_STATS",
    "WRITE_SETTINGS",
    "SCHEDULE_EXACT_ALARM",
    "USE_EXACT_ALARM",
    "QUERY_ALL_PACKAGES",
    "BIND_ACCESSIBILITY_SERVICE",
    "BIND_NOTIFICATION_LISTENER_SERVICE",
    "BIND_DEVICE_ADMIN",
    "BIND_VPN_SERVICE",
}


APP_PURPOSES = (
    "Anti-scam voice assistant",
    "Banking or UPI",
    "Video calling",
    "Navigation or maps",
    "Camera or document scanner",
    "Messaging or social media",
    "Health and fitness",
    "Shopping or e-commerce",
    "Game",
    "Education",
    "Utility or productivity",
    "Other",
)

PURPOSE_PROFILES: dict[str, dict[str, set[str]]] = {
    "Anti-scam voice assistant": {
        "expected": {
            "RECORD_AUDIO",
            "INTERNET",
            "ACCESS_NETWORK_STATE",
            "POST_NOTIFICATIONS",
            "FOREGROUND_SERVICE",
            "WAKE_LOCK",
        },
        "possible": {
            "READ_PHONE_STATE",
            "READ_PHONE_NUMBERS",
            "ANSWER_PHONE_CALLS",
            "BLUETOOTH_CONNECT",
            "RECEIVE_BOOT_COMPLETED",
            "USE_BIOMETRIC",
        },
        "critical_mismatch": {
            "READ_SMS",
            "RECEIVE_SMS",
            "SEND_SMS",
            "READ_CALL_LOG",
            "WRITE_CALL_LOG",
            "READ_CONTACTS",
            "WRITE_CONTACTS",
            "ACCESS_FINE_LOCATION",
            "ACCESS_BACKGROUND_LOCATION",
            "MANAGE_EXTERNAL_STORAGE",
            "REQUEST_INSTALL_PACKAGES",
            "BIND_ACCESSIBILITY_SERVICE",
            "SYSTEM_ALERT_WINDOW",
        },
    },
    "Banking or UPI": {
        "expected": {
            "INTERNET",
            "ACCESS_NETWORK_STATE",
            "POST_NOTIFICATIONS",
            "USE_BIOMETRIC",
            "CAMERA",
        },
        "possible": {
            "READ_PHONE_STATE",
            "READ_PHONE_NUMBERS",
            "RECEIVE_SMS",
            "NFC",
            "ACCESS_FINE_LOCATION",
            "BLUETOOTH_CONNECT",
        },
        "critical_mismatch": {
            "READ_CALL_LOG",
            "WRITE_CALL_LOG",
            "RECORD_AUDIO",
            "ACCESS_BACKGROUND_LOCATION",
            "MANAGE_EXTERNAL_STORAGE",
            "REQUEST_INSTALL_PACKAGES",
            "BIND_ACCESSIBILITY_SERVICE",
            "SYSTEM_ALERT_WINDOW",
        },
    },
    "Video calling": {
        "expected": {
            "CAMERA",
            "RECORD_AUDIO",
            "INTERNET",
            "ACCESS_NETWORK_STATE",
            "POST_NOTIFICATIONS",
            "FOREGROUND_SERVICE",
            "BLUETOOTH_CONNECT",
        },
        "possible": {
            "READ_CONTACTS",
            "READ_PHONE_STATE",
            "RECEIVE_BOOT_COMPLETED",
            "WAKE_LOCK",
        },
        "critical_mismatch": {
            "READ_SMS",
            "SEND_SMS",
            "READ_CALL_LOG",
            "WRITE_CALL_LOG",
            "ACCESS_BACKGROUND_LOCATION",
            "REQUEST_INSTALL_PACKAGES",
            "BIND_ACCESSIBILITY_SERVICE",
            "SYSTEM_ALERT_WINDOW",
        },
    },
    "Navigation or maps": {
        "expected": {
            "ACCESS_FINE_LOCATION",
            "ACCESS_COARSE_LOCATION",
            "ACCESS_BACKGROUND_LOCATION",
            "INTERNET",
            "ACCESS_NETWORK_STATE",
            "POST_NOTIFICATIONS",
            "FOREGROUND_SERVICE",
            "WAKE_LOCK",
        },
        "possible": {
            "BLUETOOTH_CONNECT",
            "BLUETOOTH_SCAN",
            "NEARBY_WIFI_DEVICES",
            "RECORD_AUDIO",
        },
        "critical_mismatch": {
            "READ_SMS",
            "SEND_SMS",
            "READ_CALL_LOG",
            "WRITE_CALL_LOG",
            "READ_CONTACTS",
            "REQUEST_INSTALL_PACKAGES",
            "BIND_ACCESSIBILITY_SERVICE",
        },
    },
    "Camera or document scanner": {
        "expected": {
            "CAMERA",
            "READ_MEDIA_IMAGES",
            "READ_MEDIA_VIDEO",
            "INTERNET",
            "ACCESS_NETWORK_STATE",
        },
        "possible": {
            "RECORD_AUDIO",
            "READ_EXTERNAL_STORAGE",
            "WRITE_EXTERNAL_STORAGE",
            "POST_NOTIFICATIONS",
        },
        "critical_mismatch": {
            "READ_SMS",
            "SEND_SMS",
            "READ_CALL_LOG",
            "WRITE_CALL_LOG",
            "READ_CONTACTS",
            "ACCESS_BACKGROUND_LOCATION",
            "REQUEST_INSTALL_PACKAGES",
            "BIND_ACCESSIBILITY_SERVICE",
            "SYSTEM_ALERT_WINDOW",
        },
    },
    "Messaging or social media": {
        "expected": {
            "INTERNET",
            "ACCESS_NETWORK_STATE",
            "POST_NOTIFICATIONS",
            "CAMERA",
            "RECORD_AUDIO",
            "READ_CONTACTS",
        },
        "possible": {
            "READ_MEDIA_IMAGES",
            "READ_MEDIA_VIDEO",
            "READ_MEDIA_AUDIO",
            "ACCESS_FINE_LOCATION",
            "BLUETOOTH_CONNECT",
            "WAKE_LOCK",
        },
        "critical_mismatch": {
            "READ_CALL_LOG",
            "WRITE_CALL_LOG",
            "ACCESS_BACKGROUND_LOCATION",
            "REQUEST_INSTALL_PACKAGES",
            "BIND_ACCESSIBILITY_SERVICE",
        },
    },
    "Health and fitness": {
        "expected": {
            "BODY_SENSORS",
            "BODY_SENSORS_BACKGROUND",
            "ACCESS_FINE_LOCATION",
            "ACCESS_COARSE_LOCATION",
            "INTERNET",
            "ACCESS_NETWORK_STATE",
            "POST_NOTIFICATIONS",
            "FOREGROUND_SERVICE",
        },
        "possible": {
            "BLUETOOTH_CONNECT",
            "BLUETOOTH_SCAN",
            "CAMERA",
            "RECORD_AUDIO",
        },
        "critical_mismatch": {
            "READ_SMS",
            "SEND_SMS",
            "READ_CALL_LOG",
            "WRITE_CALL_LOG",
            "READ_CONTACTS",
            "REQUEST_INSTALL_PACKAGES",
            "BIND_ACCESSIBILITY_SERVICE",
            "SYSTEM_ALERT_WINDOW",
        },
    },
    "Shopping or e-commerce": {
        "expected": {
            "INTERNET",
            "ACCESS_NETWORK_STATE",
            "POST_NOTIFICATIONS",
            "CAMERA",
        },
        "possible": {
            "ACCESS_FINE_LOCATION",
            "ACCESS_COARSE_LOCATION",
            "USE_BIOMETRIC",
            "READ_MEDIA_IMAGES",
        },
        "critical_mismatch": {
            "READ_SMS",
            "SEND_SMS",
            "READ_CALL_LOG",
            "WRITE_CALL_LOG",
            "READ_CONTACTS",
            "RECORD_AUDIO",
            "ACCESS_BACKGROUND_LOCATION",
            "REQUEST_INSTALL_PACKAGES",
            "BIND_ACCESSIBILITY_SERVICE",
            "SYSTEM_ALERT_WINDOW",
        },
    },
    "Game": {
        "expected": {
            "INTERNET",
            "ACCESS_NETWORK_STATE",
            "POST_NOTIFICATIONS",
            "VIBRATE",
            "WAKE_LOCK",
        },
        "possible": {
            "RECORD_AUDIO",
            "CAMERA",
            "BLUETOOTH_CONNECT",
            "READ_MEDIA_IMAGES",
        },
        "critical_mismatch": {
            "READ_SMS",
            "SEND_SMS",
            "READ_CALL_LOG",
            "WRITE_CALL_LOG",
            "READ_CONTACTS",
            "WRITE_CONTACTS",
            "ACCESS_BACKGROUND_LOCATION",
            "MANAGE_EXTERNAL_STORAGE",
            "REQUEST_INSTALL_PACKAGES",
            "BIND_ACCESSIBILITY_SERVICE",
            "SYSTEM_ALERT_WINDOW",
        },
    },
    "Education": {
        "expected": {
            "INTERNET",
            "ACCESS_NETWORK_STATE",
            "POST_NOTIFICATIONS",
            "CAMERA",
            "RECORD_AUDIO",
        },
        "possible": {
            "READ_MEDIA_IMAGES",
            "READ_MEDIA_VIDEO",
            "READ_EXTERNAL_STORAGE",
            "WRITE_EXTERNAL_STORAGE",
        },
        "critical_mismatch": {
            "READ_SMS",
            "SEND_SMS",
            "READ_CALL_LOG",
            "WRITE_CALL_LOG",
            "READ_CONTACTS",
            "ACCESS_BACKGROUND_LOCATION",
            "REQUEST_INSTALL_PACKAGES",
            "BIND_ACCESSIBILITY_SERVICE",
            "SYSTEM_ALERT_WINDOW",
        },
    },
    "Utility or productivity": {
        "expected": {
            "INTERNET",
            "ACCESS_NETWORK_STATE",
            "POST_NOTIFICATIONS",
        },
        "possible": {
            "CAMERA",
            "RECORD_AUDIO",
            "READ_MEDIA_IMAGES",
            "READ_MEDIA_VIDEO",
            "READ_CALENDAR",
            "WRITE_CALENDAR",
            "RECEIVE_BOOT_COMPLETED",
        },
        "critical_mismatch": {
            "READ_SMS",
            "SEND_SMS",
            "READ_CALL_LOG",
            "WRITE_CALL_LOG",
            "ACCESS_BACKGROUND_LOCATION",
            "REQUEST_INSTALL_PACKAGES",
            "BIND_ACCESSIBILITY_SERVICE",
            "SYSTEM_ALERT_WINDOW",
        },
    },
    "Other": {
        "expected": {
            "INTERNET",
            "ACCESS_NETWORK_STATE",
        },
        "possible": {
            "POST_NOTIFICATIONS",
            "CAMERA",
            "RECORD_AUDIO",
            "ACCESS_FINE_LOCATION",
            "ACCESS_COARSE_LOCATION",
            "READ_CONTACTS",
            "READ_MEDIA_IMAGES",
            "READ_MEDIA_VIDEO",
            "BLUETOOTH_CONNECT",
        },
        "critical_mismatch": {
            "READ_SMS",
            "SEND_SMS",
            "READ_CALL_LOG",
            "WRITE_CALL_LOG",
            "ACCESS_BACKGROUND_LOCATION",
            "MANAGE_EXTERNAL_STORAGE",
            "REQUEST_INSTALL_PACKAGES",
            "BIND_ACCESSIBILITY_SERVICE",
            "SYSTEM_ALERT_WINDOW",
        },
    },
}

NECESSITY_ORDER = {
    "Critical mismatch": 0,
    "Unusual": 1,
    "Possibly justified": 2,
    "Expected": 3,
}

PERMISSION_CATALOG: dict[str, dict[str, str]] = {
    "BIND_ACCESSIBILITY_SERVICE": {
        "severity": "Critical",
        "title": "Accessibility service",
        "explanation": "Can let an enabled accessibility service observe screen content and interact with other apps.",
        "legitimate_use": "Accessibility tools for users with disabilities, password managers, or tightly scoped automation.",
        "verify": "Only enable this for a developer and purpose you fully trust.",
    },
    "SYSTEM_ALERT_WINDOW": {
        "severity": "Critical",
        "title": "Display over other apps",
        "explanation": "Can place windows over other applications.",
        "legitimate_use": "Chat heads, screen tools, call overlays, or assistive interfaces.",
        "verify": "Unknown apps can misuse overlays to imitate login or payment screens.",
    },
    "REQUEST_INSTALL_PACKAGES": {
        "severity": "Critical",
        "title": "Install unknown applications",
        "explanation": "Can request installation of APK packages from outside the normal app store flow.",
        "legitimate_use": "App stores, enterprise deployment tools, browsers, or file managers.",
        "verify": "Avoid granting this to apps that do not clearly need to install other apps.",
    },
    "MANAGE_EXTERNAL_STORAGE": {
        "severity": "Critical",
        "title": "Manage all files",
        "explanation": "Can access broad areas of shared device storage.",
        "legitimate_use": "File managers, backup tools, antivirus products, or document-management apps.",
        "verify": "A simple game, calculator, or wallpaper app rarely needs broad file access.",
    },
    "BIND_DEVICE_ADMIN": {
        "severity": "Critical",
        "title": "Device administrator",
        "explanation": "A device-admin component may enforce security policies or make removal more difficult after activation.",
        "legitimate_use": "Enterprise device management, parental controls, or anti-theft tools.",
        "verify": "Do not activate device administration for an unfamiliar application.",
    },
    "BIND_NOTIFICATION_LISTENER_SERVICE": {
        "severity": "Critical",
        "title": "Notification access",
        "explanation": "An enabled notification listener can read notifications from other apps.",
        "legitimate_use": "Wearables, notification history, automation, or cross-device tools.",
        "verify": "Notifications may contain OTPs, private messages, or transaction details.",
    },
    "READ_SMS": {
        "severity": "Critical",
        "title": "Read SMS messages",
        "explanation": "Can read SMS content stored on the device.",
        "legitimate_use": "Default SMS apps or narrowly scoped message-management tools.",
        "verify": "SMS messages can contain OTPs and sensitive account information.",
    },
    "RECEIVE_SMS": {
        "severity": "Critical",
        "title": "Receive incoming SMS",
        "explanation": "Can be notified when SMS messages arrive.",
        "legitimate_use": "Default SMS apps or verified OTP workflows.",
        "verify": "Confirm why the app needs to observe incoming messages.",
    },
    "SEND_SMS": {
        "severity": "Critical",
        "title": "Send SMS messages",
        "explanation": "Can send text messages, potentially creating charges.",
        "legitimate_use": "Default messaging apps or emergency communication tools.",
        "verify": "Do not grant this to unrelated applications.",
    },
    "READ_CALL_LOG": {
        "severity": "Critical",
        "title": "Read call history",
        "explanation": "Can access phone call-history information.",
        "legitimate_use": "Default dialers, call backup, or verified communication tools.",
        "verify": "Call logs reveal sensitive relationship and contact patterns.",
    },
    "WRITE_CALL_LOG": {
        "severity": "Critical",
        "title": "Modify call history",
        "explanation": "Can add, modify, or remove call-log entries.",
        "legitimate_use": "Default dialers and specialised call-management tools.",
        "verify": "This is rarely needed outside communication applications.",
    },
    "ACCESS_BACKGROUND_LOCATION": {
        "severity": "Critical",
        "title": "Background location",
        "explanation": "Can access location even when the app is not actively in use, subject to user approval.",
        "legitimate_use": "Navigation, fitness tracking, delivery, safety, or geofencing.",
        "verify": "Check whether continuous location is essential to the app's main function.",
    },
    "PACKAGE_USAGE_STATS": {
        "severity": "High",
        "title": "Usage access",
        "explanation": "Can view information about which apps are used and when after special access is enabled.",
        "legitimate_use": "Digital wellbeing, parental controls, launchers, or productivity analytics.",
        "verify": "Usage patterns can reveal sensitive behavioural information.",
    },
    "QUERY_ALL_PACKAGES": {
        "severity": "High",
        "title": "View installed applications",
        "explanation": "Can broadly query applications installed on the device.",
        "legitimate_use": "Security scanners, launchers, backup tools, or device migration.",
        "verify": "Confirm why the app needs a complete list of installed software.",
    },
    "BIND_VPN_SERVICE": {
        "severity": "High",
        "title": "VPN service",
        "explanation": "A VPN service can route device network traffic after the user enables it.",
        "legitimate_use": "VPN, firewall, parental-control, or network-filtering products.",
        "verify": "Only trust a VPN provider whose ownership and privacy policy you can verify.",
    },
    "RECORD_AUDIO": {
        "severity": "High",
        "title": "Microphone",
        "explanation": "Can record audio while permission is granted and the platform permits access.",
        "legitimate_use": "Calls, voice notes, recording, speech recognition, or audio creation.",
        "verify": "A non-audio app should clearly explain why microphone access is necessary.",
    },
    "CAMERA": {
        "severity": "High",
        "title": "Camera",
        "explanation": "Can capture photos or video while permission is granted.",
        "legitimate_use": "Camera, scanning, video calls, identity verification, or augmented reality.",
        "verify": "Check whether image capture is part of the app's core purpose.",
    },
    "READ_CONTACTS": {
        "severity": "High",
        "title": "Read contacts",
        "explanation": "Can read names and contact information stored on the device.",
        "legitimate_use": "Messaging, calling, contact backup, or social discovery.",
        "verify": "Avoid granting this to apps with no communication-related purpose.",
    },
    "WRITE_CONTACTS": {
        "severity": "High",
        "title": "Modify contacts",
        "explanation": "Can add, change, or remove contacts.",
        "legitimate_use": "Contact-management, backup, calling, or messaging apps.",
        "verify": "Confirm the app genuinely needs to edit your address book.",
    },
    "READ_PHONE_STATE": {
        "severity": "High",
        "title": "Phone status",
        "explanation": "Can access certain phone-state and network identifiers depending on Android version and approval.",
        "legitimate_use": "Calling, carrier services, fraud prevention, or device diagnostics.",
        "verify": "Check whether phone-state access matches the app's function.",
    },
    "READ_PHONE_NUMBERS": {
        "severity": "High",
        "title": "Phone number",
        "explanation": "Can access phone-number information when available.",
        "legitimate_use": "Calling, account setup, or carrier services.",
        "verify": "The app should explain why your number is required.",
    },
    "ANSWER_PHONE_CALLS": {
        "severity": "High",
        "title": "Answer phone calls",
        "explanation": "Can answer incoming calls when permitted.",
        "legitimate_use": "Dialers, call assistants, vehicle integrations, or accessibility tools.",
        "verify": "This is unusual for apps unrelated to calling.",
    },
    "PROCESS_OUTGOING_CALLS": {
        "severity": "High",
        "title": "Monitor outgoing calls",
        "explanation": "Legacy permission associated with observing or redirecting outgoing calls.",
        "legitimate_use": "Older dialer or call-management applications.",
        "verify": "Treat this as sensitive, especially in an unfamiliar APK.",
    },
    "BODY_SENSORS_BACKGROUND": {
        "severity": "High",
        "title": "Background body sensors",
        "explanation": "Can access supported body-sensor data in the background after approval.",
        "legitimate_use": "Health and fitness tracking.",
        "verify": "Sensitive health-related data should only be shared with trusted apps.",
    },
    "ACCESS_FINE_LOCATION": {
        "severity": "Medium",
        "title": "Precise location",
        "explanation": "Can access precise device location while allowed.",
        "legitimate_use": "Maps, navigation, delivery, ride services, weather, or nearby-device features.",
        "verify": "A location-unrelated app should not normally need precise location.",
    },
    "ACCESS_COARSE_LOCATION": {
        "severity": "Medium",
        "title": "Approximate location",
        "explanation": "Can access approximate device location while allowed.",
        "legitimate_use": "Local weather, regional content, nearby services, or Bluetooth discovery on older Android versions.",
        "verify": "Check whether location improves a clear user-facing feature.",
    },
    "READ_CALENDAR": {
        "severity": "Medium",
        "title": "Read calendar",
        "explanation": "Can read calendar events.",
        "legitimate_use": "Calendar, scheduling, travel, or productivity tools.",
        "verify": "Calendar entries may contain private meeting and location details.",
    },
    "WRITE_CALENDAR": {
        "severity": "Medium",
        "title": "Modify calendar",
        "explanation": "Can add, change, or delete calendar events.",
        "legitimate_use": "Calendar, booking, scheduling, or travel apps.",
        "verify": "Confirm event editing is part of the app's purpose.",
    },
    "READ_MEDIA_IMAGES": {
        "severity": "Medium",
        "title": "Read photos",
        "explanation": "Can access images selected or permitted by the platform.",
        "legitimate_use": "Photo editing, social posting, backup, or document scanning.",
        "verify": "Prefer limited photo selection where the app supports it.",
    },
    "READ_MEDIA_VIDEO": {
        "severity": "Medium",
        "title": "Read videos",
        "explanation": "Can access videos selected or permitted by the platform.",
        "legitimate_use": "Video editing, posting, backup, or media players.",
        "verify": "A non-media app should explain this request.",
    },
    "READ_MEDIA_AUDIO": {
        "severity": "Medium",
        "title": "Read audio",
        "explanation": "Can access audio files permitted by the platform.",
        "legitimate_use": "Music players, audio editors, backup, or sharing.",
        "verify": "Check whether audio-library access is expected.",
    },
    "READ_EXTERNAL_STORAGE": {
        "severity": "Medium",
        "title": "Read shared storage",
        "explanation": "Legacy permission for reading shared device storage.",
        "legitimate_use": "File, media, backup, or document tools.",
        "verify": "Its effective scope depends on the target Android version.",
    },
    "WRITE_EXTERNAL_STORAGE": {
        "severity": "Medium",
        "title": "Write shared storage",
        "explanation": "Legacy permission for writing to shared device storage.",
        "legitimate_use": "File, media, backup, or document tools.",
        "verify": "Its effective scope depends on the target Android version.",
    },
    "BLUETOOTH_CONNECT": {
        "severity": "Medium",
        "title": "Connect to Bluetooth devices",
        "explanation": "Can connect to paired Bluetooth devices.",
        "legitimate_use": "Wearables, audio, smart-home, vehicle, or peripheral apps.",
        "verify": "Confirm Bluetooth is part of the app's main feature.",
    },
    "BLUETOOTH_SCAN": {
        "severity": "Medium",
        "title": "Scan for Bluetooth devices",
        "explanation": "Can discover nearby Bluetooth devices.",
        "legitimate_use": "Device setup, wearables, proximity, or accessories.",
        "verify": "Nearby-device scans can reveal environmental information.",
    },
    "NEARBY_WIFI_DEVICES": {
        "severity": "Medium",
        "title": "Nearby Wi-Fi devices",
        "explanation": "Can discover or interact with nearby Wi-Fi devices under supported Android versions.",
        "legitimate_use": "Device setup, casting, file transfer, or smart-home control.",
        "verify": "Check whether nearby-device interaction is expected.",
    },
    "BODY_SENSORS": {
        "severity": "Medium",
        "title": "Body sensors",
        "explanation": "Can access supported body-sensor measurements while permitted.",
        "legitimate_use": "Health and fitness applications.",
        "verify": "Treat health-related sensor data as sensitive.",
    },
    "POST_NOTIFICATIONS": {
        "severity": "Medium",
        "title": "Send notifications",
        "explanation": "Can display notifications after the user grants permission on supported Android versions.",
        "legitimate_use": "Messages, reminders, order updates, security alerts, and most interactive apps.",
        "verify": "This is common, but excessive notifications can be disruptive or deceptive.",
    },
    "SCHEDULE_EXACT_ALARM": {
        "severity": "Medium",
        "title": "Schedule exact alarms",
        "explanation": "Can request precisely timed alarms under platform rules.",
        "legitimate_use": "Alarm clocks, calendars, medication reminders, or time-critical tools.",
        "verify": "Exact alarms can affect battery use and should match a time-sensitive feature.",
    },
    "USE_EXACT_ALARM": {
        "severity": "Medium",
        "title": "Use exact alarms",
        "explanation": "Can schedule precisely timed alarms under platform rules.",
        "legitimate_use": "Alarm, calendar, or time-critical reminder apps.",
        "verify": "Confirm the app provides a clear time-critical function.",
    },
    "WRITE_SETTINGS": {
        "severity": "Medium",
        "title": "Modify system settings",
        "explanation": "Can change certain system settings after special access is enabled.",
        "legitimate_use": "Brightness, ringtone, automation, or device-management tools.",
        "verify": "Only grant this when the setting changes are expected.",
    },
    "INTERNET": {
        "severity": "Common",
        "title": "Internet access",
        "explanation": "Allows network communication.",
        "legitimate_use": "Online content, accounts, updates, cloud services, or advertising.",
        "verify": "Common permission; network destinations are not assessed in this version.",
    },
    "ACCESS_NETWORK_STATE": {
        "severity": "Common",
        "title": "Network status",
        "explanation": "Can check whether the device is connected to a network.",
        "legitimate_use": "Adapting online features to connectivity.",
        "verify": "Common and generally low concern by itself.",
    },
    "ACCESS_WIFI_STATE": {
        "severity": "Common",
        "title": "Wi-Fi status",
        "explanation": "Can inspect basic Wi-Fi connection information.",
        "legitimate_use": "Connectivity checks, casting, or local-network features.",
        "verify": "Common and generally low concern by itself.",
    },
    "VIBRATE": {
        "severity": "Common",
        "title": "Vibration",
        "explanation": "Can trigger device vibration.",
        "legitimate_use": "Notifications, feedback, games, or alarms.",
        "verify": "Common and low concern.",
    },
    "WAKE_LOCK": {
        "severity": "Common",
        "title": "Keep device awake",
        "explanation": "Can keep the processor or screen active for certain tasks.",
        "legitimate_use": "Media playback, downloads, calls, navigation, or background work.",
        "verify": "May affect battery life but is not highly sensitive by itself.",
    },
    "RECEIVE_BOOT_COMPLETED": {
        "severity": "Review",
        "title": "Start after device boot",
        "explanation": "Can receive a notification after the device finishes starting.",
        "legitimate_use": "Alarms, security, messaging, health, or scheduled background services.",
        "verify": "Check whether automatic background startup is necessary.",
    },
    "FOREGROUND_SERVICE": {
        "severity": "Common",
        "title": "Foreground service",
        "explanation": "Supports visible long-running work with a persistent notification.",
        "legitimate_use": "Navigation, calls, media playback, fitness, or file transfers.",
        "verify": "Common for legitimate long-running tasks.",
    },
    "USE_BIOMETRIC": {
        "severity": "Common",
        "title": "Biometric authentication",
        "explanation": "Allows the app to request platform biometric authentication.",
        "legitimate_use": "Login, payments, vaults, or secure confirmation.",
        "verify": "The app does not receive your raw fingerprint or face data through this permission.",
    },
    "NFC": {
        "severity": "Review",
        "title": "Near-field communication",
        "explanation": "Can use supported NFC capabilities.",
        "legitimate_use": "Payments, tags, identity documents, pairing, or transit.",
        "verify": "Check whether NFC is part of the expected feature set.",
    },
}


class APKAnalysisError(RuntimeError):
    """Raised when an uploaded file cannot be analysed as an APK."""


def _short_name(permission: str) -> str:
    return permission.rsplit(".", 1)[-1].strip()


def _humanise_permission_name(short_name: str) -> str:
    return short_name.replace("_", " ").title()


def _permission_details(full_name: str) -> dict[str, Any]:
    short_name = _short_name(full_name)
    known = PERMISSION_CATALOG.get(short_name)

    if known:
        severity = known["severity"]
        return {
            "full_name": full_name,
            "short_name": short_name,
            "title": known["title"],
            "severity": severity,
            "points": SEVERITY_POINTS[severity],
            "special_access": short_name in SPECIAL_ACCESS_PERMISSIONS,
            "explanation": known["explanation"],
            "legitimate_use": known["legitimate_use"],
            "verify": known["verify"],
            "custom_permission": not full_name.startswith("android.permission."),
        }

    if full_name.startswith("android.permission."):
        severity = "Review"
        return {
            "full_name": full_name,
            "short_name": short_name,
            "title": _humanise_permission_name(short_name),
            "severity": severity,
            "points": SEVERITY_POINTS[severity],
            "special_access": short_name in SPECIAL_ACCESS_PERMISSIONS,
            "explanation": "Android platform permission not yet included in AppVerity's detailed catalogue.",
            "legitimate_use": "Its purpose depends on the Android version and application feature.",
            "verify": "Review the official Android permission documentation and the app's stated purpose.",
            "custom_permission": False,
        }

    return {
        "full_name": full_name,
        "short_name": short_name,
        "title": _humanise_permission_name(short_name),
        "severity": "Review",
        "points": 0,
        "special_access": False,
        "explanation": "Custom permission declared by an application or third-party component.",
        "legitimate_use": "Custom permissions can protect communication between related apps or components.",
        "verify": "A custom permission is not automatically dangerous; verify its owner and use.",
        "custom_permission": True,
    }


def _risk_level(score: int) -> str:
    if score <= 20:
        return "Low"
    if score <= 50:
        return "Medium"
    return "High"


def _combination_warnings(permission_names: set[str]) -> list[str]:
    warnings: list[str] = []

    sms_permissions = {"READ_SMS", "RECEIVE_SMS", "SEND_SMS"}
    if permission_names.intersection(sms_permissions) and (
        "SYSTEM_ALERT_WINDOW" in permission_names
        or "BIND_ACCESSIBILITY_SERVICE" in permission_names
    ):
        warnings.append(
            "SMS access combined with overlay or accessibility capabilities deserves critical verification."
        )

    if {
        "REQUEST_INSTALL_PACKAGES",
        "QUERY_ALL_PACKAGES",
    }.issubset(permission_names):
        warnings.append(
            "The app can broadly view installed apps and request installation of other APKs."
        )

    if {
        "READ_CONTACTS",
        "READ_SMS",
    }.issubset(permission_names):
        warnings.append(
            "The app declares access to both contacts and SMS content."
        )

    if {
        "RECORD_AUDIO",
        "ACCESS_BACKGROUND_LOCATION",
    }.issubset(permission_names):
        warnings.append(
            "The app declares both microphone and background-location access."
        )

    if {
        "SYSTEM_ALERT_WINDOW",
        "BIND_ACCESSIBILITY_SERVICE",
    }.issubset(permission_names):
        warnings.append(
            "Overlay and accessibility capabilities together can provide extensive interaction with other apps."
        )

    return warnings


def _component_special_accesses(apk: Any) -> list[dict[str, str]]:
    """Inspect manifest component permissions not normally listed as uses-permission."""
    accesses: list[dict[str, str]] = []
    component_types = (
        ("service", apk.get_services()),
        ("receiver", apk.get_receivers()),
        ("activity", apk.get_activities()),
    )

    recognised = {
        "android.permission.BIND_ACCESSIBILITY_SERVICE": (
            "Critical",
            "Accessibility service component",
        ),
        "android.permission.BIND_NOTIFICATION_LISTENER_SERVICE": (
            "Critical",
            "Notification-listener component",
        ),
        "android.permission.BIND_DEVICE_ADMIN": (
            "Critical",
            "Device-administrator component",
        ),
        "android.permission.BIND_VPN_SERVICE": (
            "High",
            "VPN service component",
        ),
    }

    for component_type, names in component_types:
        for component_name in names:
            try:
                permission = apk.get_attribute_value(
                    component_type,
                    "permission",
                    name=component_name,
                )
            except Exception:
                permission = None

            if permission in recognised:
                severity, title = recognised[permission]
                accesses.append(
                    {
                        "component_type": component_type,
                        "component_name": component_name,
                        "permission": permission,
                        "short_name": _short_name(permission),
                        "severity": severity,
                        "title": title,
                    }
                )

    unique: dict[tuple[str, str, str], dict[str, str]] = {}
    for item in accesses:
        key = (
            item["component_type"],
            item["component_name"],
            item["permission"],
        )
        unique[key] = item

    return sorted(
        unique.values(),
        key=lambda item: (
            SEVERITY_ORDER.get(item["severity"], 99),
            item["title"],
            item["component_name"],
        ),
    )



def _necessity_label(
    short_name: str,
    purpose: str,
    severity: str,
) -> tuple[str, str]:
    profile = PURPOSE_PROFILES.get(purpose, PURPOSE_PROFILES["Other"])

    if short_name in profile["expected"]:
        return (
            "Expected",
            "This permission directly matches the selected app purpose.",
        )

    if short_name in profile["possible"]:
        return (
            "Possibly justified",
            "This permission may support an optional feature, but the developer should explain it clearly.",
        )

    if short_name in profile["critical_mismatch"]:
        return (
            "Critical mismatch",
            "This powerful permission does not normally match the selected app purpose.",
        )

    if severity in {"Critical", "High"}:
        return (
            "Unusual",
            "This sensitive permission is not normally expected for the selected app purpose.",
        )

    if severity == "Common":
        return (
            "Expected",
            "This is a common platform capability and usually does not indicate a purpose mismatch by itself.",
        )

    return (
        "Possibly justified",
        "The permission may be valid depending on the app's exact features.",
    )


def _apply_necessity_assessment(
    permission_items: list[dict[str, Any]],
    purpose: str,
) -> tuple[list[dict[str, Any]], dict[str, int], int]:
    counts: Counter[str] = Counter()
    mismatch_score = 0

    for item in permission_items:
        label, reason = _necessity_label(
            item["short_name"],
            purpose,
            item["severity"],
        )
        item["necessity"] = label
        item["necessity_reason"] = reason
        counts[label] += 1

        if label == "Critical mismatch":
            mismatch_score += 18
        elif label == "Unusual":
            mismatch_score += 8
        elif label == "Possibly justified" and item["severity"] in {"Critical", "High"}:
            mismatch_score += 3

    permission_items.sort(
        key=lambda item: (
            NECESSITY_ORDER.get(item["necessity"], 99),
            SEVERITY_ORDER.get(item["severity"], 99),
            item["short_name"],
        )
    )

    return permission_items, dict(counts), min(100, mismatch_score)


def _quick_permission_check(
    permission_names: set[str],
) -> list[dict[str, str]]:
    checks = [
        ("Camera", "CAMERA"),
        ("Microphone", "RECORD_AUDIO"),
        ("Read SMS", "READ_SMS"),
        ("Receive SMS", "RECEIVE_SMS"),
        ("Send SMS", "SEND_SMS"),
        ("Contacts", "READ_CONTACTS"),
        ("Precise location", "ACCESS_FINE_LOCATION"),
        ("Background location", "ACCESS_BACKGROUND_LOCATION"),
        ("Accessibility service", "BIND_ACCESSIBILITY_SERVICE"),
        ("Display over other apps", "SYSTEM_ALERT_WINDOW"),
        ("Install unknown apps", "REQUEST_INSTALL_PACKAGES"),
        ("Manage all files", "MANAGE_EXTERNAL_STORAGE"),
    ]

    return [
        {
            "capability": label,
            "permission": short_name,
            "requested": "Yes" if short_name in permission_names else "No",
        }
        for label, short_name in checks
    ]

def _build_report(result: dict[str, Any]) -> str:
    permission_lines = "\n".join(
        (
            f"- [{item['severity']} | {item.get('necessity', 'Not assessed')}] "
            f"{item['short_name']}: {item['explanation']} "
            f"Necessity assessment: {item.get('necessity_reason', 'Not available')}"
        )
        for item in result["permissions"]
    ) or "- No requested permissions were found."

    special_lines = "\n".join(
        (
            f"- [{item['severity']}] {item['title']}: "
            f"{item['component_name']}"
        )
        for item in result["component_special_accesses"]
    ) or "- No supported special component access was detected."

    warning_lines = "\n".join(
        f"- {warning}" for warning in result["combination_warnings"]
    ) or "- No predefined high-concern permission combination was detected."

    return f"""
APPVERITY AI — APK PERMISSION REPORT
====================================

File: {result['file_name']}
File size: {result['file_size_mb']:.2f} MB
SHA-256: {result['sha256']}

APPLICATION
-----------
App name: {result['app_name']}
Package: {result['package_name']}
Version name: {result['version_name']}
Version code: {result['version_code']}
Minimum SDK: {result['min_sdk']}
Target SDK: {result['target_sdk']}
Main activity: {result['main_activity']}

PERMISSION EXPOSURE
-------------------
Score: {result['permission_risk_score']}/100
Level: {result['permission_risk_level']}
Selected app purpose: {result['app_purpose']}
Purpose mismatch score: {result['purpose_mismatch_score']}/100
Total requested permissions: {result['total_permissions']}
Expected: {result['necessity_counts'].get('Expected', 0)}
Possibly justified: {result['necessity_counts'].get('Possibly justified', 0)}
Unusual: {result['necessity_counts'].get('Unusual', 0)}
Critical mismatch: {result['necessity_counts'].get('Critical mismatch', 0)}
Critical: {result['severity_counts'].get('Critical', 0)}
High: {result['severity_counts'].get('High', 0)}
Medium: {result['severity_counts'].get('Medium', 0)}
Review: {result['severity_counts'].get('Review', 0)}
Common: {result['severity_counts'].get('Common', 0)}

REQUESTED PERMISSIONS
---------------------
{permission_lines}

SPECIAL COMPONENT ACCESS
------------------------
{special_lines}

COMBINATION WARNINGS
--------------------
{warning_lines}

IMPORTANT LIMITATIONS
---------------------
- This is static manifest analysis. The APK was not installed or executed.
- Declared permission does not mean the user has granted it.
- Android version, runtime prompts, app role, and device policy affect actual access.
- A high score is not proof of malware; legitimate apps may require sensitive access.
- Verify the APK source, package name, developer, and signing certificate before installation.
""".strip()


def analyze_apk(
    apk_bytes: bytes,
    file_name: str,
    app_purpose: str = "Other",
) -> dict[str, Any]:
    if app_purpose not in APP_PURPOSES:
        app_purpose = "Other"

    if not apk_bytes:
        raise APKAnalysisError("The uploaded APK is empty.")

    if len(apk_bytes) > MAX_APK_SIZE_BYTES:
        raise APKAnalysisError(
            "The APK is larger than the 200 MB analysis limit."
        )

    if not file_name.lower().endswith(".apk"):
        raise APKAnalysisError("Upload a file with the .apk extension.")

    if not apk_bytes.startswith(b"PK"):
        raise APKAnalysisError(
            "The uploaded file does not have the ZIP structure expected for an APK."
        )

    try:
        with zipfile.ZipFile(__import__("io").BytesIO(apk_bytes)) as archive:
            names = set(archive.namelist())
            if "AndroidManifest.xml" not in names:
                raise APKAnalysisError(
                    "AndroidManifest.xml was not found. This does not appear to be a standard APK."
                )
            if archive.testzip() is not None:
                raise APKAnalysisError("The APK ZIP structure is damaged.")
    except zipfile.BadZipFile as exc:
        raise APKAnalysisError("The uploaded file is not a valid APK archive.") from exc

    try:
        from androguard.core.apk import APK
    except ImportError as exc:
        raise APKAnalysisError(
            "Androguard is not installed. Run: python -m pip install \"androguard~=4.1.4\""
        ) from exc

    try:
        apk = APK(apk_bytes, raw=True, testzip=True)
    except Exception as exc:
        raise APKAnalysisError(
            f"Androguard could not parse this APK: {exc}"
        ) from exc

    if not getattr(apk, "valid_apk", False):
        raise APKAnalysisError(
            "The file opened as a ZIP archive, but its Android manifest could not be validated."
        )

    requested_permissions = sorted(set(apk.get_permissions() or []))
    permission_items = [
        _permission_details(permission)
        for permission in requested_permissions
    ]
    permission_items.sort(
        key=lambda item: (
            SEVERITY_ORDER.get(item["severity"], 99),
            item["short_name"],
        )
    )

    permission_items, necessity_counts, purpose_mismatch_score = (
        _apply_necessity_assessment(permission_items, app_purpose)
    )

    component_accesses = _component_special_accesses(apk)

    permission_short_names = {
        item["short_name"] for item in permission_items
    }
    permission_short_names.update(
        item["short_name"] for item in component_accesses
    )

    base_points = sum(item["points"] for item in permission_items)
    component_points = sum(
        18 if item["severity"] == "Critical" else 9
        for item in component_accesses
        if item["short_name"] not in {
            permission["short_name"] for permission in permission_items
        }
    )
    combination_warnings = _combination_warnings(permission_short_names)
    combination_points = min(15, len(combination_warnings) * 5)

    permission_risk_score = min(
        100,
        base_points + component_points + combination_points,
    )

    severity_counts = Counter(
        item["severity"] for item in permission_items
    )
    for item in component_accesses:
        severity_counts[item["severity"]] += 1

    try:
        app_name = apk.get_app_name() or "Not available"
    except Exception:
        app_name = "Not available"

    quick_permission_check = _quick_permission_check(permission_short_names)

    result: dict[str, Any] = {
        "file_name": file_name,
        "file_size_bytes": len(apk_bytes),
        "file_size_mb": round(len(apk_bytes) / (1024 * 1024), 2),
        "sha256": hashlib.sha256(apk_bytes).hexdigest(),
        "app_name": str(app_name),
        "package_name": apk.get_package() or "Not available",
        "version_name": apk.get_androidversion_name() or "Not available",
        "version_code": apk.get_androidversion_code() or "Not available",
        "min_sdk": apk.get_min_sdk_version() or "Not available",
        "target_sdk": apk.get_target_sdk_version() or "Not available",
        "main_activity": apk.get_main_activity() or "Not available",
        "activity_count": len(apk.get_activities() or []),
        "service_count": len(apk.get_services() or []),
        "receiver_count": len(apk.get_receivers() or []),
        "provider_count": len(apk.get_providers() or []),
        "total_permissions": len(permission_items),
        "permissions": permission_items,
        "component_special_accesses": component_accesses,
        "severity_counts": dict(severity_counts),
        "combination_warnings": combination_warnings,
        "permission_risk_score": permission_risk_score,
        "permission_risk_level": _risk_level(permission_risk_score),
        "app_purpose": app_purpose,
        "necessity_counts": necessity_counts,
        "purpose_mismatch_score": purpose_mismatch_score,
        "quick_permission_check": quick_permission_check,
    }
    result["report_text"] = _build_report(result)
    return result
