using Microsoft.EntityFrameworkCore;
using Microsoft.AspNetCore.Identity.EntityFrameworkCore;

namespace Auth.Data;

public class AuthDbContext : IdentityDbContext&lt;ApplicationUser&gt;
{
    public AuthDbContext(DbContextOptions&lt;AuthDbContext&gt; options) : base(options) { }

    protected override void OnModelCreating(ModelBuilder builder)
    {
        base.OnModelCreating(builder);

        // Seed roles
        builder.Entity&lt;IdentityRole&gt;().HasData(
            new IdentityRole { Id = "1", Name = "Admin", NormalizedName = "ADMIN" },
            new IdentityRole { Id = "2", Name = "User", NormalizedName = "USER" },
            new IdentityRole { Id = "3", Name = "Agent", NormalizedName = "AGENT" } // For future MCP/LLM agents
        );
    }
}