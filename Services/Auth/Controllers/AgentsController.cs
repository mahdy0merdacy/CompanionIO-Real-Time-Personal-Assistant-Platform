using Auth.Data;
using Auth.Models;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;

namespace Auth.Controllers;

[ApiController]
[Route("api/[controller]")]
public class AgentsController : ControllerBase
{
    private readonly UserManager&lt;ApplicationUser&gt; _userManager;
    private readonly IConfiguration _configuration;

    public AgentsController(UserManager&lt;ApplicationUser&gt; userManager, IConfiguration configuration)
    {
        _userManager = userManager;
        _configuration = configuration;
    }

    [HttpPost("register")]
    [Authorize(Roles = "Admin")]
    public async Task&lt;IActionResult&gt; RegisterAgent([FromBody] AgentRegistrationRequest request)
    {
        // Create a service account for agents (MCP servers, LLM, etc.)
        var agent = new ApplicationUser
        {
            UserName = request.Name,
            Email = $"{request.Name}@agents.companionio.local",
            FullName = request.Name
        };

        var result = await _userManager.CreateAsync(agent, request.ApiKey);
        if (!result.Succeeded)
            return BadRequest("Agent registration failed");

        await _userManager.AddToRoleAsync(agent, "Agent");

        return Ok(new { AgentId = agent.Id, ApiKey = request.ApiKey });
    }

    [HttpPost("authenticate")]
    public async Task&lt;IActionResult&gt; AuthenticateAgent([FromBody] AgentAuthRequest request)
    {
        var agent = await _userManager.FindByNameAsync(request.Name);
        if (agent == null || !await _userManager.CheckPasswordAsync(agent, request.ApiKey))
            return Unauthorized();

        var token = GenerateJwtToken(agent);
        return Ok(new { Token = token });
    }

    private string GenerateJwtToken(ApplicationUser user)
    {
        var claims = new[]
        {
            new Claim(JwtRegisteredClaimNames.Sub, user.Id),
            new Claim(JwtRegisteredClaimNames.Email, user.Email),
            new Claim(JwtRegisteredClaimNames.Jti, Guid.NewGuid().ToString()),
            new Claim(ClaimTypes.Role, "Agent")
        };

        var key = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(_configuration["Jwt:Key"]));
        var creds = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);

        var token = new JwtSecurityToken(
            issuer: _configuration["Jwt:Issuer"],
            audience: _configuration["Jwt:Audience"],
            claims: claims,
            expires: DateTime.Now.AddHours(24), // Longer for agents
            signingCredentials: creds);

        return new JwtSecurityTokenHandler().WriteToken(token);
    }
}

public class AgentRegistrationRequest
{
    public string Name { get; set; }
    public string ApiKey { get; set; }
}

public class AgentAuthRequest
{
    public string Name { get; set; }
    public string ApiKey { get; set; }
}