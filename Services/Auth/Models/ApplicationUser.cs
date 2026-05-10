using Microsoft.AspNetCore.Identity;

namespace Auth.Models;

public class ApplicationUser : IdentityUser
{
    // Additional properties can be added here if needed
    public string? FullName { get; set; }
    public DateTime CreatedAt { get; set; } = DateTime.UtcNow;
}