# Problem Statement

## Background

Electrical grid operators are under increasing pressure to maintain reliable power delivery. The physical infrastructure—transformers, feeders, and substations—is aging rapidly, while extreme weather events are becoming more frequent. The power grid is fundamentally fragile; a single component failure can trigger cascading outages that affect thousands of people and critical civic infrastructure.

## The Problem

Today, utility maintenance is largely reactive or rigidly calendar-based. Operations teams dispatch repair crews only *after* a failure has occurred (causing immediate downtime), or they perform scheduled maintenance every few years regardless of whether the asset actually needs it (wasting resources). Furthermore, when predicting failures, existing models only look at sheer failure probability without understanding the *topology* of the grid, treating a highly-redundant feeder and a non-redundant hospital supply line as equally risky.

## Who is Affected

This problem directly impacts **Grid Operations Centers (Grid Ops)** and **On-Call Maintenance Crews**. 
Grid Ops teams are overwhelmed with disconnected telemetry alerts and struggle to prioritize which assets need attention today. Maintenance crews waste time driving to low-priority scheduled checks while critical transformers are silently degrading across town.

## Why It Matters

The cost of unexpected downtime is staggering. For industrial sectors and critical infrastructure, power outages cost upwards of **$1M+ per hour**. Beyond the financial damage, un-backed-up outages that hit hospitals, water treatment plants, or schools pose severe public safety risks. Every minute saved by proactively pre-positioning a crew before a failure translates directly to preserved revenue and safety.

## Why Existing Solutions Fall Short

Existing solutions either rely on purely reactive SCADA alerts or generic ML models that output a simple "probability of failure." They fall short in two major ways:
1. **Lack of Topology Awareness:** A 60% chance of failure on a residential line is treated as worse than a 40% chance of failure on a hospital's sole power line. 
2. **Siloed Data:** Sensor telemetry (IoT) and environmental data (Weather) are rarely fused dynamically. A degrading transformer might survive a mild week but fail catastrophically during an impending heatwave, a reality that current siloed systems miss entirely.
