# Capsha Design Philosophy

English | [日本語](DESIGN.ja.md)

## Launch → Capture → Annotate

Capsha is a lightweight tool for adding annotations to screenshots quickly. It is not trying to become a full-featured image editor.

The core flow is:

1. Launch Capsha.
2. Capture a region immediately.
3. Add only the annotations needed to share the screenshot.

## Principles

### Launch means capture

Starting Capsha should start capture. Do not add a home screen, startup menu, or mode picker to the normal launch path.

### Speed over features

Startup speed, capture speed, and interaction responsiveness matter more than feature count.

### Every feature must earn its place

Every button, dialog, and setting has a cost. Before adding one, ask:

> Can we achieve the same result without adding another button, dialog, or setting?

### Simplicity is a feature

Capsha should feel obvious. Prefer small, direct interactions over configurable workflows.

### Great defaults beat endless options

Choose defaults that work well for most screenshots. Add settings only when there is no simpler way to solve the problem.

### Respect the user's flow

The user is usually trying to share something, not edit an image. Keep the path from capture to clipboard, save, or share as short as possible.

### Philosophy before features

When deciding what to build next, start with the product philosophy:

Capture. Annotate. Share.

New work should make Capsha faster, simpler, or more intuitive. If it does not clearly support that goal, it should wait.
