# Nscale plugin for Waldur Site Agent

This plugin provides Nscale integration capabilities for Waldur Site Agent.

## Installation

See the main [Installation Guide](../../docs/installation.md) for platform-specific installation instructions.

## Configuration

The Nscale plugin requires the following configuration:

### Required Settings

- `api_url`: The base URL for the Nscale API
- `organization_id`: Your Nscale organization ID
- `project_id`: Your Nscale project ID
- `service_token`: Service token for API authentication (generated in Nscale Console)

### Optional Settings

- `resource_prefix`: Prefix for resource names (default: "waldur_")
- `default_instance_type`: Default instance type for compute resources (default: "standard")
- `default_image_id`: Default image ID for compute instances
- `default_network_id`: Default network ID to use for resources
- `default_security_group_ids`: List of default security group IDs

## Resources Supported

The Nscale plugin supports the following resource types:

- **Networks**: Virtual networks for resource isolation
- **Security Groups**: Network security rules
- **Compute Instances**: Virtual machines
- **Compute Clusters**: Clustered compute resources

## Component Mapping

Components in Waldur map to resource specifications in Nscale:

- `cpu`: CPU cores/vCPUs
- `memory`: Memory in MB/GB
- `storage`: Storage in GB

Each component can have:
- `accounting_type`: "limit" (limit-based accounting)
- `unit_factor`: Factor to convert between Waldur and Nscale units
- `measured_unit`: Unit of measurement (e.g., "core-hours", "GB")

## Example Configuration

See `examples/nscale-config.yaml` in this plugin directory for a complete configuration example.

## API Documentation

For detailed API documentation, refer to:
- [Nscale Terraform Provider](https://github.com/nscaledev/terraform-provider-nscale)
- [Nscale Go Client](https://github.com/nscaledev/uni-client-go)
- [Nscale API Docs](https://github.com/nscaledev/uni-api-docs)

## Notes

- The plugin uses HTTP REST API to communicate with Nscale
- Service tokens should be rotated regularly for security
- Resource creation may require pre-existing networks and security groups
- User associations may need to be configured based on your Nscale setup
