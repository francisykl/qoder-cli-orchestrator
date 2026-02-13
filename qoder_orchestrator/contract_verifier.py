#!/usr/bin/env python3
"""
API contract verification for frontend/backend integration.
Ensures contracts stay in sync across components.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class APIEndpoint:
    """Represents an API endpoint."""
    path: str
    method: str
    request_schema: Optional[Dict] = None
    response_schema: Optional[Dict] = None
    description: str = ""


@dataclass
class APIContract:
    """Complete API contract."""
    component: str  # "backend" or "frontend"
    endpoints: Dict[str, APIEndpoint] = field(default_factory=dict)
    models: Dict[str, Dict] = field(default_factory=dict)


@dataclass
class ContractMismatch:
    """Represents a contract mismatch."""
    endpoint_path: str
    mismatch_type: str  # "missing", "schema_diff", "method_diff"
    backend_value: Optional[any] = None
    frontend_value: Optional[any] = None
    severity: str = "error"  # "error", "warning"
    suggestion: str = ""


class ContractExtractor:
    """Extracts API contracts from code."""
    
    def __init__(self, project_dir: Path):
        """
        Initialize contract extractor.
        
        Args:
            project_dir: Project directory path
        """
        self.project_dir = project_dir
    
    def extract_from_openapi(self, spec_file: Path) -> APIContract:
        """
        Extract contract from OpenAPI specification.
        
        Args:
            spec_file: Path to OpenAPI spec file
            
        Returns:
            APIContract
        """
        contract = APIContract(component="backend")
        
        try:
            with open(spec_file, 'r') as f:
                spec = json.load(f) if spec_file.suffix == '.json' else {}
            
            # Extract endpoints
            paths = spec.get('paths', {})
            for path, methods in paths.items():
                for method, details in methods.items():
                    if method.upper() in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
                        endpoint = APIEndpoint(
                            path=path,
                            method=method.upper(),
                            description=details.get('description', ''),
                            request_schema=details.get('requestBody', {}).get('content', {}).get('application/json', {}).get('schema'),
                            response_schema=details.get('responses', {}).get('200', {}).get('content', {}).get('application/json', {}).get('schema')
                        )
                        contract.endpoints[f"{method.upper()} {path}"] = endpoint
            
            # Extract models
            components = spec.get('components', {})
            schemas = components.get('schemas', {})
            contract.models = schemas
            
            logger.info(f"Extracted {len(contract.endpoints)} endpoints from OpenAPI spec")
            
        except Exception as e:
            logger.error(f"Failed to extract from OpenAPI spec: {e}")
        
        return contract
    
    def extract_from_backend_code(self, backend_dir: Path) -> APIContract:
        """
        Extract contract from backend code (Python/FastAPI/Flask).
        
        Args:
            backend_dir: Backend directory path
            
        Returns:
            APIContract
        """
        contract = APIContract(component="backend")
        
        # Simple pattern matching for common frameworks
        # In production, use AST parsing
        
        for py_file in backend_dir.rglob("*.py"):
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                
                # Look for FastAPI route decorators
                fastapi_routes = re.findall(
                    r'@app\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']\)',
                    content,
                    re.IGNORECASE
                )
                
                for method, path in fastapi_routes:
                    endpoint_key = f"{method.upper()} {path}"
                    if endpoint_key not in contract.endpoints:
                        contract.endpoints[endpoint_key] = APIEndpoint(
                            path=path,
                            method=method.upper()
                        )
                
            except Exception as e:
                logger.debug(f"Failed to parse {py_file}: {e}")
        
        logger.info(f"Extracted {len(contract.endpoints)} endpoints from backend code")
        return contract
    
    def extract_from_frontend_code(self, frontend_dir: Path) -> APIContract:
        """
        Extract contract from frontend code (JavaScript/TypeScript).
        
        Args:
            frontend_dir: Frontend directory path
            
        Returns:
            APIContract
        """
        contract = APIContract(component="frontend")
        
        # Look for API calls in frontend code
        for js_file in frontend_dir.rglob("*.{js,ts,jsx,tsx}"):
            try:
                with open(js_file, 'r') as f:
                    content = f.read()
                
                # Look for fetch/axios calls
                api_calls = re.findall(
                    r'(fetch|axios)\s*\(\s*[\'"`]([^\'"` ]+)[\'"`]\s*,?\s*\{[^}]*method:\s*[\'"`](\w+)[\'"`]',
                    content,
                    re.IGNORECASE
                )
                
                for _, path, method in api_calls:
                    endpoint_key = f"{method.upper()} {path}"
                    if endpoint_key not in contract.endpoints:
                        contract.endpoints[endpoint_key] = APIEndpoint(
                            path=path,
                            method=method.upper()
                        )
                
            except Exception as e:
                logger.debug(f"Failed to parse {js_file}: {e}")
        
        logger.info(f"Extracted {len(contract.endpoints)} endpoints from frontend code")
        return contract


class ContractVerifier:
    """Verifies API contracts between frontend and backend."""
    
    def __init__(self, project_dir: Path):
        """
        Initialize contract verifier.
        
        Args:
            project_dir: Project directory path
        """
        self.project_dir = project_dir
        self.extractor = ContractExtractor(project_dir)
    
    def verify_contracts(
        self,
        backend_contract: APIContract,
        frontend_contract: APIContract
    ) -> List[ContractMismatch]:
        """
        Verify contracts match between frontend and backend.
        
        Args:
            backend_contract: Backend API contract
            frontend_contract: Frontend API contract
            
        Returns:
            List of mismatches
        """
        mismatches = []
        
        # Check for endpoints in frontend not in backend
        for endpoint_key, frontend_endpoint in frontend_contract.endpoints.items():
            if endpoint_key not in backend_contract.endpoints:
                mismatches.append(ContractMismatch(
                    endpoint_path=frontend_endpoint.path,
                    mismatch_type="missing",
                    backend_value=None,
                    frontend_value=endpoint_key,
                    severity="error",
                    suggestion=f"Add endpoint {endpoint_key} to backend"
                ))
        
        # Check for endpoints in backend not in frontend
        for endpoint_key, backend_endpoint in backend_contract.endpoints.items():
            if endpoint_key not in frontend_contract.endpoints:
                mismatches.append(ContractMismatch(
                    endpoint_path=backend_endpoint.path,
                    mismatch_type="missing",
                    backend_value=endpoint_key,
                    frontend_value=None,
                    severity="warning",
                    suggestion=f"Endpoint {endpoint_key} not used by frontend"
                ))
        
        # Check for schema mismatches (if available)
        common_endpoints = set(backend_contract.endpoints.keys()) & set(frontend_contract.endpoints.keys())
        
        for endpoint_key in common_endpoints:
            backend_ep = backend_contract.endpoints[endpoint_key]
            frontend_ep = frontend_contract.endpoints[endpoint_key]
            
            # Compare methods
            if backend_ep.method != frontend_ep.method:
                mismatches.append(ContractMismatch(
                    endpoint_path=backend_ep.path,
                    mismatch_type="method_diff",
                    backend_value=backend_ep.method,
                    frontend_value=frontend_ep.method,
                    severity="error",
                    suggestion=f"Method mismatch: backend uses {backend_ep.method}, frontend uses {frontend_ep.method}"
                ))
        
        return mismatches
    
    def generate_report(self, mismatches: List[ContractMismatch]) -> str:
        """
        Generate human-readable report of contract mismatches.
        
        Args:
            mismatches: List of mismatches
            
        Returns:
            Formatted report string
        """
        if not mismatches:
            return "✓ All API contracts are in sync"
        
        errors = [m for m in mismatches if m.severity == "error"]
        warnings = [m for m in mismatches if m.severity == "warning"]
        
        report = []
        report.append("\n" + "="*60)
        report.append("API CONTRACT VERIFICATION REPORT")
        report.append("="*60)
        
        if errors:
            report.append(f"\n❌ ERRORS ({len(errors)}):")
            for mismatch in errors:
                report.append(f"\n  Endpoint: {mismatch.endpoint_path}")
                report.append(f"  Type: {mismatch.mismatch_type}")
                if mismatch.backend_value:
                    report.append(f"  Backend: {mismatch.backend_value}")
                if mismatch.frontend_value:
                    report.append(f"  Frontend: {mismatch.frontend_value}")
                report.append(f"  → {mismatch.suggestion}")
        
        if warnings:
            report.append(f"\n⚠️  WARNINGS ({len(warnings)}):")
            for mismatch in warnings:
                report.append(f"\n  Endpoint: {mismatch.endpoint_path}")
                report.append(f"  → {mismatch.suggestion}")
        
        report.append("\n" + "="*60 + "\n")
        
        return "\n".join(report)


def verify_api_contracts(project_dir: Path) -> List[ContractMismatch]:
    """
    Convenience function to verify API contracts.
    
    Args:
        project_dir: Project directory path
        
    Returns:
        List of contract mismatches
    """
    verifier = ContractVerifier(project_dir)
    extractor = verifier.extractor
    
    # Try to find backend and frontend directories
    backend_dir = project_dir / "backend"
    frontend_dir = project_dir / "frontend"
    
    if not backend_dir.exists():
        backend_dir = project_dir / "server"
    if not frontend_dir.exists():
        frontend_dir = project_dir / "client"
    
    # Extract contracts
    backend_contract = extractor.extract_from_backend_code(backend_dir) if backend_dir.exists() else APIContract("backend")
    frontend_contract = extractor.extract_from_frontend_code(frontend_dir) if frontend_dir.exists() else APIContract("frontend")
    
    # Verify
    mismatches = verifier.verify_contracts(backend_contract, frontend_contract)
    
    # Print report
    report = verifier.generate_report(mismatches)
    print(report)
    
    return mismatches
