using Hangfire;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace Auth.Controllers;

[ApiController]
[Route("api/[controller]")]
public class AuditController : ControllerBase
{
    [HttpPost("log")]
    [Authorize]
    public IActionResult LogAuditEvent([FromBody] AuditEvent auditEvent)
    {
        // Queue audit logging as background job
        BackgroundJob.Enqueue(() => ProcessAuditLog(auditEvent));
        return Ok();
    }

    [NonAction]
    public void ProcessAuditLog(AuditEvent auditEvent)
    {
        // Simulate audit logging (in real app, write to database/file)
        Console.WriteLine($"Audit: {auditEvent.Action} by {auditEvent.UserId} at {auditEvent.Timestamp}");
    }
}

public class AuditEvent
{
    public string UserId { get; set; }
    public string Action { get; set; }
    public DateTime Timestamp { get; set; } = DateTime.UtcNow;
    public string Details { get; set; }
}