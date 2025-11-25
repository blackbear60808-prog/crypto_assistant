# modules/audit_system.py
import sqlite3
import json
from datetime import datetime
import logging
from typing import Dict, List, Any

class AuditSystem:
    """操作審計系統 - 記錄所有系統操作和審計日誌"""
    
    def __init__(self, db):
        self.db = db
        self.logger = logging.getLogger('AuditSystem')
        self.setup_audit_tables()
    
    def setup_audit_tables(self):
        """設置審計資料表"""
        try:
            cursor = self.db.conn.cursor()
            
            # 操作審計表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    user_id TEXT,
                    action_type TEXT NOT NULL,
                    action_description TEXT NOT NULL,
                    resource_type TEXT,
                    resource_id TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    status TEXT,
                    error_message TEXT,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 敏感操作表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sensitive_operations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    user_id TEXT,
                    operation_type TEXT NOT NULL,
                    description TEXT NOT NULL,
                    risk_level TEXT,
                    approval_required BOOLEAN DEFAULT FALSE,
                    approved_by TEXT,
                    approved_at DATETIME,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 系統變更表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_changes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    change_type TEXT NOT NULL,
                    component TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    changed_by TEXT,
                    reason TEXT,
                    rollback_possible BOOLEAN DEFAULT FALSE,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 權限審計表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS permission_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    user_id TEXT,
                    permission_type TEXT NOT NULL,
                    target_resource TEXT,
                    action TEXT,
                    granted_by TEXT,
                    revoked_by TEXT,
                    effective_from DATETIME,
                    effective_until DATETIME,
                    metadata TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            self.db.conn.commit()
            self.logger.info("審計資料表創建完成")
            
        except Exception as e:
            self.logger.error(f"創建審計資料表錯誤: {e}")
    
    def log_operation(self, action_type: str, description: str, user_id: str = None, 
                     resource_type: str = None, resource_id: str = None,
                     status: str = "SUCCESS", error_message: str = None,
                     metadata: Dict = None):
        """記錄一般操作"""
        try:
            cursor = self.db.conn.cursor()
            
            cursor.execute('''
                INSERT INTO audit_logs 
                (timestamp, user_id, action_type, action_description, resource_type, 
                 resource_id, status, error_message, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                user_id,
                action_type,
                description,
                resource_type,
                resource_id,
                status,
                error_message,
                json.dumps(metadata) if metadata else None
            ))
            
            self.db.conn.commit()
            self.logger.info(f"操作記錄: {action_type} - {description}")
            return True
            
        except Exception as e:
            self.logger.error(f"記錄操作錯誤: {e}")
            return False
    
    def log_sensitive_operation(self, operation_type: str, description: str, 
                               user_id: str = None, risk_level: str = "MEDIUM",
                               approval_required: bool = False, metadata: Dict = None):
        """記錄敏感操作"""
        try:
            cursor = self.db.conn.cursor()
            
            cursor.execute('''
                INSERT INTO sensitive_operations 
                (timestamp, user_id, operation_type, description, risk_level, 
                 approval_required, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                user_id,
                operation_type,
                description,
                risk_level,
                approval_required,
                json.dumps(metadata) if metadata else None
            ))
            
            self.db.conn.commit()
            self.logger.warning(f"敏感操作記錄: {operation_type} - {description} (風險等級: {risk_level})")
            return cursor.lastrowid
            
        except Exception as e:
            self.logger.error(f"記錄敏感操作錯誤: {e}")
            return None
    
    def approve_sensitive_operation(self, operation_id: int, approved_by: str):
        """批准敏感操作"""
        try:
            cursor = self.db.conn.cursor()
            
            cursor.execute('''
                UPDATE sensitive_operations 
                SET approved_by = ?, approved_at = ?
                WHERE id = ?
            ''', (approved_by, datetime.now().isoformat(), operation_id))
            
            self.db.conn.commit()
            self.logger.info(f"敏感操作已批准: ID={operation_id}, 批准人={approved_by}")
            return True
            
        except Exception as e:
            self.logger.error(f"批准敏感操作錯誤: {e}")
            return False
    
    def log_system_change(self, change_type: str, component: str, 
                         old_value: str = None, new_value: str = None,
                         changed_by: str = None, reason: str = None,
                         rollback_possible: bool = False, metadata: Dict = None):
        """記錄系統變更"""
        try:
            cursor = self.db.conn.cursor()
            
            cursor.execute('''
                INSERT INTO system_changes 
                (timestamp, change_type, component, old_value, new_value, 
                 changed_by, reason, rollback_possible, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                change_type,
                component,
                old_value,
                new_value,
                changed_by,
                reason,
                rollback_possible,
                json.dumps(metadata) if metadata else None
            ))
            
            self.db.conn.commit()
            self.logger.info(f"系統變更記錄: {component} - {change_type}")
            return True
            
        except Exception as e:
            self.logger.error(f"記錄系統變更錯誤: {e}")
            return False
    
    def log_permission_change(self, user_id: str, permission_type: str, 
                             action: str, granted_by: str = None,
                             target_resource: str = None, metadata: Dict = None):
        """記錄權限變更"""
        try:
            cursor = self.db.conn.cursor()
            
            cursor.execute('''
                INSERT INTO permission_audit 
                (timestamp, user_id, permission_type, target_resource, action, 
                 granted_by, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                user_id,
                permission_type,
                target_resource,
                action,
                granted_by,
                json.dumps(metadata) if metadata else None
            ))
            
            self.db.conn.commit()
            self.logger.info(f"權限變更記錄: {user_id} - {permission_type} - {action}")
            return True
            
        except Exception as e:
            self.logger.error(f"記錄權限變更錯誤: {e}")
            return False
    
    def get_audit_logs(self, days: int = 7, action_type: str = None, 
                      user_id: str = None, limit: int = 100):
        """獲取審計日誌"""
        try:
            cursor = self.db.conn.cursor()
            
            query = '''
                SELECT timestamp, user_id, action_type, action_description, 
                       resource_type, resource_id, status, error_message
                FROM audit_logs 
                WHERE timestamp >= datetime('now', ?)
            '''
            params = [f'-{days} days']
            
            if action_type:
                query += ' AND action_type = ?'
                params.append(action_type)
            
            if user_id:
                query += ' AND user_id = ?'
                params.append(user_id)
            
            query += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            return cursor.fetchall()
            
        except Exception as e:
            self.logger.error(f"獲取審計日誌錯誤: {e}")
            return []
    
    def get_sensitive_operations(self, days: int = 30, risk_level: str = None,
                               approved_only: bool = False, limit: int = 50):
        """獲取敏感操作記錄"""
        try:
            cursor = self.db.conn.cursor()
            
            query = '''
                SELECT timestamp, user_id, operation_type, description, 
                       risk_level, approval_required, approved_by, approved_at
                FROM sensitive_operations 
                WHERE timestamp >= datetime('now', ?)
            '''
            params = [f'-{days} days']
            
            if risk_level:
                query += ' AND risk_level = ?'
                params.append(risk_level)
            
            if approved_only:
                query += ' AND approved_by IS NOT NULL'
            
            query += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            return cursor.fetchall()
            
        except Exception as e:
            self.logger.error(f"獲取敏感操作錯誤: {e}")
            return []
    
    def get_system_changes(self, days: int = 30, component: str = None, 
                          change_type: str = None, limit: int = 50):
        """獲取系統變更記錄"""
        try:
            cursor = self.db.conn.cursor()
            
            query = '''
                SELECT timestamp, change_type, component, old_value, new_value,
                       changed_by, reason, rollback_possible
                FROM system_changes 
                WHERE timestamp >= datetime('now', ?)
            '''
            params = [f'-{days} days']
            
            if component:
                query += ' AND component = ?'
                params.append(component)
            
            if change_type:
                query += ' AND change_type = ?'
                params.append(change_type)
            
            query += ' ORDER BY timestamp DESC LIMIT ?'
            params.append(limit)
            
            cursor.execute(query, params)
            return cursor.fetchall()
            
        except Exception as e:
            self.logger.error(f"獲取系統變更錯誤: {e}")
            return []
    
    def generate_audit_report(self, start_date: str, end_date: str, report_type: str = "summary"):
        """生成審計報告"""
        try:
            report = {
                'report_type': report_type,
                'period': f"{start_date} 至 {end_date}",
                'generated_at': datetime.now().isoformat(),
                'summary': {},
                'details': []
            }
            
            # 統計各類操作數量
            cursor = self.db.conn.cursor()
            
            # 操作統計
            cursor.execute('''
                SELECT action_type, status, COUNT(*) as count
                FROM audit_logs 
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY action_type, status
            ''', (start_date, end_date))
            
            action_stats = cursor.fetchall()
            report['summary']['operation_stats'] = action_stats
            
            # 敏感操作統計
            cursor.execute('''
                SELECT risk_level, COUNT(*) as count
                FROM sensitive_operations 
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY risk_level
            ''', (start_date, end_date))
            
            sensitive_stats = cursor.fetchall()
            report['summary']['sensitive_operation_stats'] = sensitive_stats
            
            # 系統變更統計
            cursor.execute('''
                SELECT change_type, COUNT(*) as count
                FROM system_changes 
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY change_type
            ''', (start_date, end_date))
            
            change_stats = cursor.fetchall()
            report['summary']['system_change_stats'] = change_stats
            
            self.logger.info(f"審計報告生成成功: {report_type}")
            return report
            
        except Exception as e:
            self.logger.error(f"生成審計報告錯誤: {e}")
            return None
    
    def export_audit_data(self, file_path: str, data_type: str = "all", days: int = 30):
        """導出審計數據"""
        try:
            export_data = {
                'export_time': datetime.now().isoformat(),
                'data_type': data_type,
                'period_days': days
            }
            
            if data_type in ["all", "operations"]:
                export_data['audit_logs'] = self.get_audit_logs(days=days, limit=1000)
            
            if data_type in ["all", "sensitive"]:
                export_data['sensitive_operations'] = self.get_sensitive_operations(days=days, limit=500)
            
            if data_type in ["all", "changes"]:
                export_data['system_changes'] = self.get_system_changes(days=days, limit=500)
            
            # 保存到文件
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=4, ensure_ascii=False)
            
            self.logger.info(f"審計數據導出成功: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"導出審計數據錯誤: {e}")
            return False