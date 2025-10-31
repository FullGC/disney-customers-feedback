"""OpenTelemetry instrumentation configuration for the Disney Customer Feedback API."""
from __future__ import annotations

import logging
from typing import Any

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)


def setup_telemetry(app: Any, service_name: str = "disney-customer-feedback-api") -> None:
    """Set up OpenTelemetry instrumentation for the FastAPI application.
    
    Args:
        app: The FastAPI application instance.
        service_name: Name of the service for telemetry.
    """
    # Create resource with service information
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0",
        "deployment.environment": "development"
    })
    
    # Set up tracing
    setup_tracing(resource)
    
    # Set up metrics
    setup_metrics(resource)
    
    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)
    
    # Instrument HTTPX (for OpenAI and ChromaDB calls)
    HTTPXClientInstrumentor().instrument()
    
    logger.info(f"OpenTelemetry instrumentation configured for {service_name}")


def setup_tracing(resource: Resource) -> None:
    """Configure distributed tracing with OTLP exporter.
    
    Args:
        resource: OpenTelemetry resource with service information.
    """
    # Create OTLP trace exporter (sends to OpenTelemetry Collector)
    otlp_exporter = OTLPSpanExporter(
        endpoint="http://localhost:4318/v1/traces",
        timeout=10
    )
    
    # Create tracer provider
    tracer_provider = TracerProvider(resource=resource)
    
    # Add batch span processor
    tracer_provider.add_span_processor(
        BatchSpanProcessor(otlp_exporter)
    )
    
    # Set as global tracer provider
    trace.set_tracer_provider(tracer_provider)
    
    logger.info("Tracing configured with OTLP exporter")


def setup_metrics(resource: Resource) -> None:
    """Configure metrics collection with OTLP exporter.
    
    Args:
        resource: OpenTelemetry resource with service information.
    """
    # Create OTLP metric exporter
    otlp_exporter = OTLPMetricExporter(
        endpoint="http://localhost:4318/v1/metrics",
        timeout=10
    )
    
    # Create metric reader with periodic export
    metric_reader = PeriodicExportingMetricReader(
        exporter=otlp_exporter,
        export_interval_millis=10000  # Export every 10 seconds
    )
    
    # Create meter provider
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=[metric_reader]
    )
    
    # Set as global meter provider
    metrics.set_meter_provider(meter_provider)
    
    logger.info("Metrics configured with OTLP exporter")


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer for creating custom spans.
    
    Args:
        name: Name of the tracer (typically module name).
        
    Returns:
        Tracer instance.
    """
    return trace.get_tracer(name)


def get_meter(name: str) -> metrics.Meter:
    """Get a meter for creating custom metrics.
    
    Args:
        name: Name of the meter (typically module name).
        
    Returns:
        Meter instance.
    """
    return metrics.get_meter(name)
