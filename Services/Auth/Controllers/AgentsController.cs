using Auth.Data;
using Auth.Models;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;

namespace Auth.Controllers;

[ApiController]
[Route("api/[controller]")]
public class AgentsController : ControllerBase
{
    private readonly UserManager<ApplicationUser> _userManager;
    private readonly IConfiguration _configuration;

    public AgentsController(UserManager<ApplicationUser> userManager, IConfiguration configuration)
    {
        _userManager = userManager;
        _configuration = configuration;
    }

    [HttpPost("register")]
    [Authorize(Roles = "Admin")]
    public async Task<IActionResult> RegisterAgent([FromBody] AgentRegistrationRequest request)
    {
        // Create a service account for agents (MCP servers, LLM, etc.)
        var agent = new ApplicationUser
        {
            UserName = request.Name,
            Email = request.Email
        };

        var result = await _userManager.CreateAsync(agent, request.Password);
        if (!result.Succeeded)
            return BadRequest(result.Errors);

        await _userManager.AddToRoleAsync(agent, "Agent");
        return Ok(new { message = "Agent registered successfully", agentId = agent.Id });
    }

    [HttpPost("authenticate")]
    public async Task<IActionResult> AuthenticateAgent([FromBody] AgentAuthRequest request)
    {
        var agent = await _userManager.FindByNameAsync(request.Name);
        if (agent == null || !await _userManager.CheckPasswordAsync(agent, request.Password))
            return Unauthorized();

        var token = GenerateJwt(agent);
        return Ok(new { token });
    }

    private string GenerateJwt(ApplicationUser user)
    {
        var key = new SymmetricSecurityKey(
            System.Text.Encoding.UTF8.GetBytes(_configuration["Jwt:Key"] ?? ""));
        var credentials = new SigningCredentials(key, SecurityAlgorithms.HmacSha256);

        var token = new JwtSecurityToken(
            issuer: _configuration["Jwt:Issuer"],
            audience: _configuration["Jwt:Audience"],
            claims: new[] { new Claim(ClaimTypes.NameIdentifier, user.Id) },
            expires: DateTime.UtcNow.AddHours(1),
            signingCredentials: credentials
        );

        return new JwtSecurityTokenHandler().WriteToken(token);
    }
}

public record AgentRegistrationRequest(string Name, string Email, string Password);
public record AgentAuthRequest(string Name, string Password);
