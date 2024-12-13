Parse [this page on Boulder history](https://www.bouldercoloradousa.com/travel-info/boulder-history/) and use it for experiments & evals in vector search


# Anatomy of the Dockerfile

1. **Multi-Stage Builds**
- Reduces final image size significantly
- Separates build-time dependencies from runtime dependencies
- Improves security by not including build tools in the final image

Note: The two-stage approach typically reduces image size by 50-70% because the final image doesn't include:
- Build tools (gcc, make, etc.), Git
- Development headers
- Temporary build files
- Source code of compiled dependencies

2. **Stage 1 (Builder)**
- Contains all build dependencies (build-essential, python3-dev, etc.)
- Creates and uses a virtual environment
- Installs all Python packages
- Only temporary - won't be in the final image

3. **Stage 2 (Runtime)**
- Starts fresh with a clean slim image
- Copies only the virtual environment from the builder
- Installs only runtime dependencies (libpq5 for PostgreSQL)
- Results in a much smaller and more secure final image

## Highlights
- Python virtual environment support
- Includes Python environment optimizations
- Uses non-root user for security
- Includes healthcheck
- Grouped environment variables
- Exposes ports
- Optimized layer caching
- Git available for e.g. pip installs from repos
- PG support (not really needed: can remove references to `libpq-dev` & `libpq5`)
