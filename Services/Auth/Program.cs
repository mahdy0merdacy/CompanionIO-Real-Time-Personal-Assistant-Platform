using Auth.Data;
using Auth.Models;
using DotNetEnv;
using Microsoft.AspNetCore.Authentication.Google;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.RateLimiting;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using Microsoft.OpenApi.Models;
using Serilog;
using System.Text;

static string? FindEnvFile()
{
    var current = Directory.GetCurrentDirectory();
    for (var i = 0; i < 5; i++)
    {
        var candidate = Path.Combine(current, ".env");
        if (File.Exists(candidate))
        {
            return candidate;
        }

        current = Path.GetDirectoryName(current) ?? string.Empty;
        if (string.IsNullOrEmpty(current))
        {
            break;
        }
    }

    current = AppContext.BaseDirectory;
    for (var i = 0; i < 5; i++)
    {
        var candidate = Path.Combine(current, ".env");
        if (File.Exists(candidate))
        {
            return candidate;
        }

        current = Path.GetDirectoryName(current) ?? string.Empty;
        if (string.IsNullOrEmpty(current))
        {
            break;
        }
    }

    return null;
}

var envFilePath = FindEnvFile();
if (!string.IsNullOrEmpty(envFilePath))
{
    Env.Load(envFilePath);
}

var builder = WebApplication.CreateBuilder(args);

// Add services to the container.
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(options =>
{
    options.AddSecurityDefinition("Bearer", new Microsoft.OpenApi.Models.OpenApiSecurityScheme
    {
        Name = "Authorization",
        Type = Microsoft.OpenApi.Models.SecuritySchemeType.Http,
        Scheme = "bearer",
        BearerFormat = "JWT",
        Description = "JWT Authorization header using the Bearer scheme."
    });
});

// Database context (PostgreSQL in production, SQLite in development)
var connectionString = builder.Configuration.GetConnectionString("DefaultConnection");
var pgHost = Environment.GetEnvironmentVariable("PGHOST");

if (!string.IsNullOrEmpty(pgHost))
{
    var pgUser = Environment.GetEnvironmentVariable("PGUSER") ?? "postgres";
    var pgPassword = Environment.GetEnvironmentVariable("PGPASSWORD") ?? string.Empty;
    var pgDatabase = Environment.GetEnvironmentVariable("PGDATABASE") ?? "authdb";
    var pgPort = Environment.GetEnvironmentVariable("PGPORT") ?? "5432";

    connectionString = $"Host={pgHost};Port={pgPort};Database={pgDatabase};Username={pgUser};Password={pgPassword};Ssl Mode=Require;Trust Server Certificate=true";
    builder.Services.AddDbContext<AuthDbContext>(options =>
        options.UseNpgsql(connectionString));
}
else if (builder.Environment.IsDevelopment())
{
    // Use SQLite for development/testing
    builder.Services.AddDbContext<AuthDbContext>(options =>
        options.UseSqlite("Data Source=auth_dev.db"));
}
else
{
    // Fallback to default (will fail if no connection string)
    builder.Services.AddDbContext<AuthDbContext>(options =>
        options.UseNpgsql(connectionString));
}

// Identity
builder.Services.AddIdentity<ApplicationUser, IdentityRole>()
    .AddEntityFrameworkStores<AuthDbContext>()
    .AddDefaultTokenProviders();

// JWT Authentication
builder.Services.AddAuthentication(options =>
{
    options.DefaultAuthenticateScheme = "Bearer";
    options.DefaultChallengeScheme = "Bearer";
})
.AddJwtBearer("Bearer", options =>
{
    options.TokenValidationParameters = new TokenValidationParameters
    {
        ValidateIssuer = true,
        ValidateAudience = true,
        ValidateLifetime = true,
        ValidateIssuerSigningKey = true,
        ValidIssuer = builder.Configuration["Jwt:Issuer"],
        ValidAudience = builder.Configuration["Jwt:Audience"],
        IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(builder.Configuration["Jwt:Key"]))
    };
})
.AddGoogle(GoogleDefaults.AuthenticationScheme, options =>
{
    options.ClientId = builder.Configuration["Google:ClientId"];
    options.ClientSecret = builder.Configuration["Google:ClientSecret"];
    options.CallbackPath = "/api/auth/google-callback";
});

builder.Services.AddAuthorization();

builder.Services.AddRateLimiter(options =>
{
    options.AddFixedWindowLimiter("fixed", opt =>
    {
        opt.Window = TimeSpan.FromMinutes(1);
        opt.PermitLimit = 100;
    });
});

// Logging with Serilog
//builder.Host.UseSerilog((context, config) =>
//{
//    config.ReadFrom.Configuration(context.Configuration);
//});//

var app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}

//app.UseHttpsRedirection();
app.UseRateLimiter();
app.UseAuthentication();
app.UseAuthorization();

app.MapControllers();

// Seed database
using (var scope = app.Services.CreateScope())
{
    var dbContext = scope.ServiceProvider.GetRequiredService<AuthDbContext>();
    try
    {
        // Apply pending migrations
        dbContext.Database.Migrate();
    }
    catch (Exception ex)
    {
        Console.WriteLine($"Migration failed: {ex.Message}. Attempting to create database schema...");
        try
        {
            // Ensure all tables are created
            dbContext.Database.EnsureCreated();
        }
        catch (Exception ex2)
        {
            Console.WriteLine($"EnsureCreated failed: {ex2.Message}");
        }
    }
}

app.Run();
