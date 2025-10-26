"""
Simple web server for SMS Forwarder monitoring
"""

from flask import Flask, render_template, jsonify
import logging
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class WebServer:
    """Simple Flask web server for monitoring"""

    def __init__(self, notification_db, devices, port=8080):
        """
        Initialize web server

        Args:
            notification_db: NotificationDB instance
            devices: List of SMSDeviceAT instances
            port: Port to run web server on (default: 8080)
        """
        self.app = Flask(__name__)
        self.db = notification_db
        self.devices = devices
        self.port = port

        # Setup routes
        self._setup_routes()

        # Disable Flask's default logging to avoid cluttering our logs
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.WARNING)

    def _setup_routes(self):
        """Setup Flask routes"""

        @self.app.route('/')
        def index():
            """Main page showing status and messages"""
            # Get device status
            devices_status = []
            for device in self.devices:
                if device.ser and device.ser.is_open:
                    try:
                        # Get signal strength
                        signal = device.get_signal_strength()
                        signal_str = f"{signal}%" if signal is not None else "N/A"

                        # Get SMS count
                        count_info = device.get_sms_count("ME")
                        sms_count = f"{count_info['used']}/{count_info['total']}" if count_info else "N/A"

                        # Get network registration
                        network_reg = device.get_network_registration()

                        device_status = {
                            'name': device.device_name,
                            'port': device.port,
                            'status': 'Connected',
                            'signal': signal_str,
                            'sms_count': sms_count,
                            'network': network_reg.get('stat_str') if network_reg else 'N/A',
                            'technology': network_reg.get('act_str') if network_reg and network_reg.get('act_str') else 'N/A',
                            'lac': network_reg.get('lac') if network_reg else None,
                            'ci': network_reg.get('ci') if network_reg else None
                        }
                    except Exception as e:
                        device_status = {
                            'name': device.device_name,
                            'port': device.port,
                            'status': f'Error: {str(e)}',
                            'signal': 'N/A',
                            'sms_count': 'N/A',
                            'network': 'N/A',
                            'technology': 'N/A',
                            'lac': None,
                            'ci': None
                        }
                else:
                    device_status = {
                        'name': device.device_name,
                        'port': device.port,
                        'status': 'Disconnected',
                        'signal': 'N/A',
                        'sms_count': 'N/A',
                        'network': 'N/A',
                        'technology': 'N/A',
                        'lac': None,
                        'ci': None
                    }

                devices_status.append(device_status)

            # Get all notifications from database
            notifications = self.db.get_recent_notifications(limit=1000)

            # Format timestamps
            for notif in notifications:
                if isinstance(notif['timestamp'], str):
                    try:
                        dt = datetime.fromisoformat(notif['timestamp'])
                        notif['timestamp_formatted'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                    except:
                        notif['timestamp_formatted'] = notif['timestamp']
                else:
                    notif['timestamp_formatted'] = notif['timestamp']

            # Get database statistics
            stats = self.db.get_stats()

            return render_template('index.html',
                                   devices=devices_status,
                                   notifications=notifications,
                                   stats=stats,
                                   current_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        @self.app.route('/api/status')
        def api_status():
            """API endpoint for device status (for future use)"""
            devices_status = []
            for device in self.devices:
                if device.ser and device.ser.is_open:
                    try:
                        signal = device.get_signal_strength()
                        count_info = device.get_sms_count("ME")
                        network_reg = device.get_network_registration()

                        device_status = {
                            'name': device.device_name,
                            'port': device.port,
                            'status': 'connected',
                            'signal': signal,
                            'sms_count': count_info,
                            'network_reg': network_reg
                        }
                    except Exception as e:
                        device_status = {
                            'name': device.device_name,
                            'port': device.port,
                            'status': 'error',
                            'error': str(e)
                        }
                else:
                    device_status = {
                        'name': device.device_name,
                        'port': device.port,
                        'status': 'disconnected'
                    }

                devices_status.append(device_status)

            return jsonify({'devices': devices_status})

    def run(self):
        """Start the web server"""
        logger.info(f"Starting web server on port {self.port}")
        logger.info(f"Web UI available at: http://localhost:{self.port}")
        self.app.run(host='0.0.0.0', port=self.port, debug=False, use_reloader=False)
